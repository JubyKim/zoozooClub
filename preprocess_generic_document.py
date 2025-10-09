import re
import json
import os
import logging
import sys
import shutil
from collections import Counter
from pathlib import Path
from config import DefaultConfig
from transformers import pipeline
from kiwipiepy import Kiwi
import sqlite3
from datetime import datetime
import hashlib
import torch

# 상수 정의
MAX_TEXT_LENGTH = 1000
BATCH_SIZE = 1000
COMMIT_INTERVAL = 10
FORCE_REBUILD = True

def setup_logging():
    if __name__ == "__main__":
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    return logging.getLogger(__name__)

logger = setup_logging()

# 기존 모델 로딩 코드...
model_name = "EbanLee/kobart-summary-v3"
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, ignore_mismatched_sizes=True)
    summarizer = pipeline("text2text-generation", model=model, tokenizer=tokenizer)
    logger.info(f"Successfully loaded summarization model: {model_name}")
except Exception as e:
    logger.error(f"Error loading summarization model '{model_name}': {e}")
    summarizer = None

try:
    kiwi = Kiwi()
    logger.info("Successfully loaded Kiwi morpheme analyzer")
except Exception as e:
    logger.error(f"Error instantiating Kiwi: {e}")
    kiwi = None

def create_faiss_index(db_path, faiss_index_path):
    """전처리 완료 후 FAISS 인덱스 생성"""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.docstore.document import Document
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        logger.info("FAISS 인덱스 생성 시작...")
        
        # 임베딩 모델 로드
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small",   # ← small로 교체 (빠르고 메모리 적음)
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        
        
        documents = []
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chapter, article, title, text, keywords, 
                       filename, reguser, url, tags
                FROM processed_chunks
            """)
            
            for row in cursor.fetchall():
                chapter, article, title, text, keywords_json, filename, reguser, url, tags_json = row
                
                # 키워드 파싱
                try:
                    keywords = json.loads(keywords_json) if keywords_json else []
                except:
                    keywords = []
                
                # 컨텐츠 강화
                enriched_parts = []
                if chapter:
                    enriched_parts.append(f"챕터: {chapter}")
                if title:
                    enriched_parts.append(f"제목: {title}")
                if article:
                    enriched_parts.append(f"조항: {article}")
                if keywords:
                    enriched_parts.append(f"키워드: {', '.join(keywords)}")
                
                enriched_parts.append(f"내용: {text}")
                enriched_content = "\n".join(enriched_parts)
                
                # 메타데이터 구성
                metadata = {
                    "source": filename,
                    "chapter": chapter or "",
                    "title": title or "",
                    "article": article or "",
                    "keywords": keywords,
                    "reguser": reguser or "",
                    "url": url or ""
                }
                
                documents.append(Document(page_content=enriched_content, metadata=metadata))
        
        if not documents:
            logger.warning("문서가 없어 FAISS 인덱스를 생성할 수 없습니다.")
            return
        
        # 텍스트 분할
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, 
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        texts = text_splitter.split_documents(documents)
        logger.info(f"Created {len(texts)} text chunks for FAISS")
        
        # FAISS 인덱스 생성
        vectorstore = FAISS.from_documents(texts, embeddings)
        
        # 저장
        faiss_index_path.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(faiss_index_path))
        
        # 메타데이터 저장
        metadata = {"created_at": datetime.now().isoformat()}
        with open(faiss_index_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
        
        logger.info("FAISS 인덱스 생성 및 저장 완료")
        
    except ImportError as e:
        logger.error(f"FAISS 관련 라이브러리를 가져올 수 없습니다: {e}")
    except Exception as e:
        logger.error(f"FAISS 인덱스 생성 중 오류: {e}")

def clean_all_data(db_path, export_dir, faiss_path):
    """모든 데이터 삭제 (FAISS 인덱스 포함)"""
    if not FORCE_REBUILD:
        return
        
    logger.warning("FORCE_REBUILD=True: 모든 기존 데이터를 삭제합니다...")
    
    # 데이터베이스 파일 삭제
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Database file deleted: {db_path}")
        except Exception as e:
            logger.error(f"Error deleting database: {e}")
    
    # JSON 출력 디렉토리 삭제
    if os.path.exists(export_dir):
        try:
            shutil.rmtree(export_dir)
            logger.info(f"Export directory deleted: {export_dir}")
        except Exception as e:
            logger.error(f"Error deleting export directory: {e}")
    
    # FAISS 인덱스 디렉토리 삭제
    if os.path.exists(faiss_path):
        try:
            shutil.rmtree(faiss_path)
            logger.info(f"FAISS index directory deleted: {faiss_path}")
        except Exception as e:
            logger.error(f"Error deleting FAISS directory: {e}")
    
    logger.info("모든 기존 데이터가 삭제되었습니다. 새로 생성합니다.")

# 기존 함수들 유지...
def generate_content_hash(text, filename, chapter="", article=""):
    content_string = f"{filename}|{chapter}|{article}|{text}"
    return hashlib.md5(content_string.encode('utf-8')).hexdigest()

def get_file_modification_time(file_path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
    except Exception:
        return datetime.now().isoformat()

def check_file_needs_processing(cursor, filename, file_mod_time):
    if FORCE_REBUILD:
        return True
        
    cursor.execute("""
        SELECT COUNT(*), MAX(file_modified) FROM processed_chunks 
        WHERE filename = ?
    """, (filename,))
    
    result = cursor.fetchone()
    if result[0] == 0:
        return True
    
    last_processed = result[1]
    if last_processed and last_processed >= file_mod_time:
        logger.info(f"File '{filename}' is up to date. Skipping.")
        return False
    
    logger.info(f"File '{filename}' has been modified. Reprocessing.")
    return True

def truncate_text_safely(text, max_length=MAX_TEXT_LENGTH):
    if len(text) <= max_length:
        return text
    
    sentences = re.split(r'[.!?]\s+', text[:max_length + 100])
    if len(sentences) > 1:
        truncated = '. '.join(sentences[:-1]) + '.'
        if len(truncated) <= max_length:
            return truncated
    
    words = text[:max_length].split()
    return ' '.join(words[:-1]) if len(words) > 1 else text[:max_length]

def generate_summary(text):
    if not text or not summarizer:
        return ""
    
    text = truncate_text_safely(text)

    try:
        summary_list = summarizer(
            text,
            max_new_tokens=100,
            min_length=20,
            do_sample=True,
            top_k=50,
            top_p=0.95
        )
        
        if summary_list and 'generated_text' in summary_list[0]:
            return summary_list[0]['generated_text']
        else:
            return ""

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return ""

def generate_keywords(text, summary_text=""):
    if not kiwi:
        return []

    combined_text = f"{text} {summary_text}".strip()
    if not combined_text:
        return []

    try:
        analysis_result = kiwi.analyze(combined_text)
        
        if not analysis_result or len(analysis_result) == 0:
            return []
        
        if len(analysis_result[0]) == 0:
            return []
            
        tokens = analysis_result[0][0]
        
        all_nouns = [
            token.form for token in tokens
            if token.tag in ['NNG', 'NNP'] and len(token.form) > 1
        ]
    
        if not all_nouns:
            return []
        
        count = Counter(all_nouns)
        return [n for n, _ in count.most_common(5)]

    except Exception as e:
        logger.error(f"Error in generate_keywords: {e}")
        return []

def create_chunk(chapter, article, title, text, config, filename, chunk_id, file_mod_time):
    summary = generate_summary(text)
    keywords = generate_keywords(text, summary)
    content_hash = generate_content_hash(text, filename, chapter, article)
    
    return {
        "chapter": chapter,
        "article": article,
        "title": title,
        "text": text,
        "keywords": keywords,
        "summary": summary,
        "reguser": config.get("reguser", ""),
        "regdate": config.get("regdate", ""),
        "uptdate": config.get("uptdate", ""),
        "filename": filename,
        "url": "",
        "tags": [f"chunk_{chunk_id}"],
        "content_hash": content_hash,
        "file_modified": file_mod_time
    }

def validate_file_path(file_path, base_directory):
    try:
        resolved_path = Path(file_path).resolve()
        base_path = Path(base_directory).resolve()
        
        if hasattr(resolved_path, 'is_relative_to'):
            return resolved_path.is_relative_to(base_path)
        else:
            try:
                resolved_path.relative_to(base_path)
                return True
            except ValueError:
                return False
                
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False

def clean_document_content(file_content, config):
    lines = file_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        skip_line = False
        for rule in config.get("cleaning_rules", []):
            rule_type = rule.get("type", "")
            pattern = rule.get("pattern", "")
            
            if rule_type == "startswith" and line.strip().startswith(pattern):
                skip_line = True
                break
            elif rule_type == "contains" and pattern in line:
                skip_line = True
                break
            elif rule_type == "exact" and line.strip() == pattern:
                skip_line = True
                break
                
        if not skip_line:
            cleaned_lines.append(line)

    cleaned_text = "\n".join(filter(None, [line.strip() for line in cleaned_lines]))
    return re.sub(r'\n\s*\n', '\n\n', cleaned_text)

def validate_regex_groups(match, expected_groups):
    if not match:
        return False
    return match.lastindex and match.lastindex >= expected_groups

def process_document_chunks(cleaned_text, config, filename, file_mod_time):
    chunks = []
    current_chapter_full = ""
    current_article_content = []
    current_article_number = ""
    current_article_title = ""
    chunk_sequence_id = 0

    try:
        chapter_pattern = re.compile(config.get("chapter_regex", r'^$'))
        article_pattern = re.compile(config.get("article_regex", r'^$'))
    except re.error as e:
        logger.error(f"Regex compilation error: {e}")
        return []

    processed_lines = cleaned_text.split('\n')

    for line in processed_lines:
        try:
            chapter_match = chapter_pattern.match(line)
            article_match = article_pattern.match(line)

            if chapter_match and validate_regex_groups(chapter_match, 2):
                if current_article_content:
                    chunk_text = "\n".join(current_article_content).strip()
                    if chunk_text:
                        chunk = create_chunk(
                            current_chapter_full, current_article_number, 
                            current_article_title, chunk_text, config, 
                            filename, chunk_sequence_id, file_mod_time
                        )
                        chunks.append(chunk)
                        chunk_sequence_id += 1
                
                current_article_content = []
                current_article_number = ""
                current_article_title = ""

                try:
                    current_chapter_full = config["chapter_format"].format(
                        chapter_match.group(1), chapter_match.group(2).strip()
                    )
                except (IndexError, KeyError) as e:
                    logger.error(f"Chapter format error: {e}")
                    current_chapter_full = line
                continue

            if article_match and validate_regex_groups(article_match, 2):
                if current_article_content:
                    chunk_text = "\n".join(current_article_content).strip()
                    if chunk_text:
                        chunk = create_chunk(
                            current_chapter_full, current_article_number,
                            current_article_title, chunk_text, config,
                            filename, chunk_sequence_id, file_mod_time
                        )
                        chunks.append(chunk)
                        chunk_sequence_id += 1
                
                current_article_content = []
                try:
                    current_article_number = config["article_format"].format(article_match.group(1))
                    current_article_title = article_match.group(2).strip()
                except (IndexError, KeyError) as e:
                    logger.error(f"Article format error: {e}")
                    current_article_number = line
                    current_article_title = ""
                
                current_article_content.append(line)
            elif current_article_number:
                current_article_content.append(line)
        
        except Exception as e:
            logger.error(f"Error processing line '{line}': {e}")
            continue

    if current_article_content:
        chunk_text = "\n".join(current_article_content).strip()
        if chunk_text:
            chunk = create_chunk(
                current_chapter_full, current_article_number,
                current_article_title, chunk_text, config,
                filename, chunk_sequence_id, file_mod_time
            )
            chunks.append(chunk)

    return chunks

def preprocess_generic_document(file_content, config, filename, file_mod_time):
    cleaned_text = clean_document_content(file_content, config)
    chunks = process_document_chunks(cleaned_text, config, filename, file_mod_time)
    return chunks

def export_processed_data_to_json(db_path, output_dir):
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM processed_chunks ORDER BY filename, id")
            
            grouped_data = {}
            
            while True:
                rows = cursor.fetchmany(BATCH_SIZE)
                if not rows:
                    break
                
                for row in rows:
                    chunk_dict = dict(row)
                    
                    for field in ['id', 'content_hash', 'file_modified']:
                        chunk_dict.pop(field, None)
                    
                    for field in ['keywords', 'tags']:
                        if chunk_dict.get(field):
                            try:
                                chunk_dict[field] = json.loads(chunk_dict[field])
                            except json.JSONDecodeError:
                                chunk_dict[field] = []
                    
                    filename_base = os.path.splitext(chunk_dict['filename'])[0]
                    if filename_base not in grouped_data:
                        grouped_data[filename_base] = []
                    grouped_data[filename_base].append(chunk_dict)
            
            os.makedirs(output_dir, exist_ok=True)
            for filename_base, chunks_list in grouped_data.items():
                safe_filename = "".join(
                c for c in filename_base 
                    if c.isalnum() or c in (' ', '-', '_')
                ).rstrip()
                
                if not safe_filename:
                    safe_filename = "unnamed_document"
                
                output_file_path = os.path.join(output_dir, f"{safe_filename}.json")
                
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(chunks_list, f, ensure_ascii=False, indent=2)
                logger.info(f"Exported {len(chunks_list)} chunks to '{output_file_path}'")

    except sqlite3.Error as e:
        logger.error(f"Error exporting data from SQLite DB: {e}")
    except Exception as e:
        logger.error(f"General error during export: {e}")

def initialize_database(db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter TEXT,
                    article TEXT,
                    title TEXT,
                    text TEXT NOT NULL,
                    keywords TEXT,
                    summary TEXT,
                    reguser TEXT,
                    regdate TEXT,
                    uptdate TEXT,
                    filename TEXT NOT NULL,
                    url TEXT,
                    tags TEXT,
                    content_hash TEXT UNIQUE,
                    file_modified TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_filename 
                ON processed_chunks(filename)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash 
                ON processed_chunks(content_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_modified 
                ON processed_chunks(filename, file_modified)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def remove_old_file_data(cursor, filename):
    cursor.execute("DELETE FROM processed_chunks WHERE filename = ?", (filename,))
    deleted_count = cursor.rowcount
    if deleted_count > 0:
        logger.info(f"Removed {deleted_count} old chunks for file '{filename}'")

def process_files(docs_directory, base_config, db_path):
    processed_count = 0
    
    txt_files = [f for f in Path(docs_directory).iterdir() 
                 if f.is_file() and f.suffix == '.txt']
    
    if not txt_files:
        logger.warning("처리할 .txt 파일이 없습니다.")
        return 0
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for file_path in txt_files:
                filename = file_path.name
                
                if not validate_file_path(str(file_path), docs_directory):
                    logger.warning(f"Invalid file path detected: {file_path}")
                    continue

                file_mod_time = get_file_modification_time(str(file_path))
                
                if not check_file_needs_processing(cursor, filename, file_mod_time):
                    continue

                logger.info(f"'{filename}' 파일 전처리 시작...")

                if FORCE_REBUILD or check_file_needs_processing(cursor, filename, file_mod_time):
                    remove_old_file_data(cursor, filename)

                config = base_config.copy()
                config["source_name"] = filename

                try:
                    content = file_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {e}")
                    continue

                processed_chunks = preprocess_generic_document(content, config, filename, file_mod_time)

                if not processed_chunks:
                    logger.warning(f"No chunks generated for file: {filename}")
                    continue

                chunk_data = []
                for chunk in processed_chunks:
                    keywords_json = json.dumps(chunk.get("keywords", []), ensure_ascii=False)
                    tags_json = json.dumps(chunk.get("tags", []), ensure_ascii=False)
                    
                    chunk_data.append((
                        chunk.get("chapter"), chunk.get("article"), chunk.get("title"), 
                        chunk.get("text"), keywords_json, chunk.get("summary"), 
                        chunk.get("reguser"), chunk.get("regdate"), chunk.get("uptdate"), 
                        chunk.get("filename"), chunk.get("url"), tags_json,
                        chunk.get("content_hash"), chunk.get("file_modified")
                    ))
                
                try:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO processed_chunks (
                            chapter, article, title, text, keywords, summary,
                            reguser, regdate, uptdate, filename, url, tags,
                            content_hash, file_modified
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, chunk_data)
                    
                    inserted_count = cursor.rowcount
                    logger.info(f"Inserted {inserted_count} new chunks for '{filename}'")
                    
                except sqlite3.IntegrityError as e:
                    logger.warning(f"Some chunks already exist for '{filename}': {e}")
                
                processed_count += 1
                
                if processed_count % COMMIT_INTERVAL == 0:
                    conn.commit()
                    logger.info(f"Committed {processed_count} files to database")
                
                logger.info(f"전처리된 {len(chunk_data)}개 청크가 처리되었습니다.")
            
            conn.commit()
                
    except sqlite3.Error as e:
        logger.error(f"Database error during file processing: {e}")
        raise
    
    return processed_count

def main():
    config = DefaultConfig()
    
    docs_directory = config.DOCS_DIRECTORY
    config_file_path = config.PREPROCESS_CONFIG_FILE_PATH
    processed_db_path = os.path.join(config.DOCS_DIRECTORY, "processed_documents.db")
    export_json_output_dir = os.path.join(config.DOCS_DIRECTORY, "exported_json_chunks")
    faiss_index_path = Path(config.DOCS_DIRECTORY) / "faiss_index"

    try:
        if FORCE_REBUILD:
            logger.warning("⚠️  FORCE_REBUILD=True: 모든 기존 데이터를 삭제하고 새로 생성합니다!")
            clean_all_data(processed_db_path, export_json_output_dir, faiss_index_path)
        else:
            logger.info("FORCE_REBUILD=False: 변경된 파일만 처리합니다.")

        with open(config_file_path, 'r', encoding='utf-8') as f:
            base_config = json.load(f)

        if not os.path.isdir(docs_directory):
            raise FileNotFoundError(f"디렉토리를 찾을 수 없습니다: {docs_directory}")

        initialize_database(processed_db_path)

        processed_count = process_files(docs_directory, base_config, processed_db_path)
        
        if processed_count > 0:
            logger.info(f"{processed_count}개 파일 처리 완료")
            logger.info("JSON 파일 추출 시작")
            export_processed_data_to_json(processed_db_path, export_json_output_dir)
            logger.info("JSON 파일 추출 완료")
            logger.info("FAISS 인덱스 생성 시작")
            create_faiss_index(processed_db_path, faiss_index_path)
            logger.info("FAISS 인덱스 생성 완료")
        else:
            if FORCE_REBUILD:
                logger.warning("처리할 파일이 없습니다.")
            else:
                logger.info("모든 파일이 최신 상태입니다.")

        return 0

    except FileNotFoundError as e:
        logger.error(f"파일을 찾을 수 없습니다: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"설정 파일 '{config_file_path}'이(가) 유효한 JSON 형식이 아닙니다: {e}")
        return 1
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
