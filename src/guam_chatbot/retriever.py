"""FAISS 벡터스토어 로드 + retriever 생성.

다른 모듈(tools/guide.py 등)에서 `from guam_chatbot.retriever import retriever`로 가져다 씀.
03_rag_test.ipynb에서 검증된 설정을 그대로 옮김 (k=3, similarity).
"""
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_upstage import UpstageEmbeddings

# .env 로드 (UpstageEmbeddings가 환경변수에서 API 키를 읽음)
# 이미 다른 곳에서 load_dotenv() 했어도 무해 — 어디서 import해도 안전
load_dotenv()

# Embedding 모델 — 02_build_index와 같은 모델이어야 함 (반드시 일치)
embeddings = UpstageEmbeddings(model="solar-embedding-1-large-query")

# FAISS 인덱스 경로
# 이 파일(retriever.py) 위치 기준으로 프로젝트 루트 경로를 계산
#   - __file__ = .../src/guam_chatbot/retriever.py
#   - .parent           → src/guam_chatbot/
#   - .parent.parent    → src/
#   - .parent.parent.parent → 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent
INDEX_DIR = PROJECT_ROOT / "data" / "faiss_index"

# allow_dangerous_deserialization=True: FAISS는 pickle 기반이라 명시 동의 필요.
# 본인이 02_build_index에서 저장한 인덱스라 안전.
vectorstore = FAISS.load_local(
    str(INDEX_DIR),
    embeddings,
    allow_dangerous_deserialization=True,
)

# Retriever — 03_rag_test에서 검증된 설정 (k=3, similarity)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})