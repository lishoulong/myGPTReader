import os
import re
import openai
import json
import math
import hashlib
import platform
import traceback
import concurrent.futures
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List
from sklearn.cluster import KMeans
from utils.thread import setup_logger
COMPLETIONS_MODEL = "gpt-3.5-turbo"
EMBEDDING_MODEL = "text-embedding-ada-002"
CONTEXT_TOKEN_LIMIT = 1500
TOKENS_PER_TOPIC = 2000
TOPIC_NUM_MIN = 3
TOPIC_NUM_MAX = 10
logging = setup_logger('my_gpt_reader_gpt')


def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    folder = 'embeddings/cache/'
    Path(folder).mkdir(parents=True, exist_ok=True)
    tmpfile = folder+hashlib.md5(text.encode('utf-8')).hexdigest()+".json"
    if os.path.isfile(tmpfile):
        with open(tmpfile, 'r', encoding='UTF-8') as f:
            return json.load(f)
    result = openai.Embedding.create(
        model=model,
        input=text
    )

    with open(tmpfile, 'w', encoding='utf-8') as handle2:
        json.dump(result["data"][0]["embedding"],
                  handle2, ensure_ascii=False, indent=4)

    return result["data"][0]["embedding"]


def get_embeddings(texts: List[str], model: str = EMBEDDING_MODEL, num_workers: int = 4) -> List[List[float]]:
    # Process the texts in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_embeddings = {executor.submit(
            get_single_embedding, text, model): text for text in texts}
        embeddings = []
        max_length = 0
        for future in concurrent.futures.as_completed(future_to_embeddings):
            embedding = np.array(future.result())
            # Find the maximum length of the embeddings
            max_length = max(max_length, len(embedding))
            embeddings.append(embedding)
    # Ensure all embeddings have the same length
    embeddings = [np.concatenate([e, np.zeros(
        max_length - len(e))]) if len(e) != max_length else e for e in embeddings]
    return embeddings


def get_single_embedding(text: str, model: str = EMBEDDING_MODEL) -> List[float]:
    result = openai.Embedding.create(
        model=model,
        input=text
    )
    return result.data[0]["embedding"]


def summarize_source(sources, embeddings):
    try:
        logging.info(f"summarize_source start")
        if not sources:
            return []
        matrix = np.vstack(embeddings)
        logging.info(f"Length of embeddings: {len(embeddings)}")
        df = pd.DataFrame({"embedding": np.array(
            embeddings).tolist(), "p": sources})

        n_clusters = get_topic_num(sources)
        n_clusters = max(1, min(n_clusters, len(matrix) - 1))
        logging.info(f"n_clusters n_clusters: {n_clusters}")
        kmeans = KMeans(n_clusters=n_clusters,
                        init="k-means++", random_state=42)
        kmeans.fit(matrix)
        df["Cluster"] = kmeans.labels_

        # Step 1: Generate summaries for each cluster
        cluster_summaries = []
        for i in range(n_clusters):
            ctx = u""
            ps = df[df.Cluster == i].p.values
            for x in ps:
                if len(ctx) + len(x) > CONTEXT_TOKEN_LIMIT:
                    logging.info(
                        f'len(ctx) + len(x)> CONTEXT_TOKEN_LIMIT -> {len(ctx) + len(x)} -> ctx is {ctx}')
                    continue
                ctx += u"\n"+x
            prompt = u"give a detail summarize based on the context\n\nContext:" + \
                ctx+u"\n\nAnswer with the language Chinese, the summarize is:"
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
            logging.info(
                f"summarize_source single ->>>> {prompt}, result ->>>> {completion.choices[0].message.content}")
            cluster_summaries.append(completion.choices[0].message.content)

        # Step 2: Generate a final summary based on the cluster summaries
        combined_context = u"<br>".join(cluster_summaries)
        # new_prompt = u"delete the head and tail messages about the website, give a detailed summarize based on the context\n\nContext:" + \
        #     combined_context+u"\n\nAnswer with the language Chinese, the answer is:"
        # new_completion = openai.ChatCompletion.create(
        #     model="gpt-3.5-turbo", messages=[{"role": "user", "content": new_prompt}])
        # logging.info(f"new_completion -> {new_completion}")
        return combined_context
    except Exception as e:
        logging.error(f"summarize_source error -> {e}")
        traceback.print_exc()


def file2embedding(folder, contents=None, batch_size=10, num_workers=4):
    try:
        if not contents:
            return None
        sources = [paragraph.strip() for content in contents for paragraph in re.split(
            r'\n\s*\n', content.strip()) if paragraph.strip() != '']
        logging.info(
            f"file2embedding folder -> {folder}, contents -> {len(contents)}, sources -> {len(sources)}")
        # Divide the sources into chunks to process in parallel
        source_chunks = [sources[i:i + batch_size]
                         for i in range(0, len(sources), batch_size)]
        # 扁平化 sources 列表
        source_texts = [text for chunk in source_chunks for text in chunk]
        logging.info(f"source_texts ->>>>>> -> {len(source_texts)}")
        # Process the source chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 修改为 text 作为键，future 作为值
            future_to_embeddings = {text: executor.submit(
                get_single_embedding, text) for text in source_texts}
            embeddings = []
            max_length = 0
            for text in source_texts:
                logging.info(f"source_texts text -> {len(text)}")
                future = future_to_embeddings[text]
                embedding = np.array(future.result())
                max_length = max(max_length, len(embedding))
                embeddings.append(embedding)
        # fly 的普通机器调用下面方法会 OOM
        summarizes = ""
        logging.info(f"platform.system() -> {platform.system()}")
        if platform.system() != 'Linux':
            summarizes = summarize_source(sources, embeddings)
        embeddings_list = [list(embedding) for embedding in embeddings]
        with open(folder, 'w', encoding='utf-8') as handle2:
            json.dump({"sources": sources, "embeddings": embeddings_list,
                      "summarizes": summarizes}, handle2, ensure_ascii=False, indent=4)
        return {"sources": sources, "embeddings": embeddings, "summarizes": summarizes}
    except Exception as e:
        logging.error(f"file2embedding error -> {e}")
        traceback.print_exc()


def get_topic_num(sources):
    num = math.floor(len("".join(sources))/TOKENS_PER_TOPIC)
    if num < TOPIC_NUM_MIN:
        return TOPIC_NUM_MIN
    if num > TOPIC_NUM_MAX:
        return TOPIC_NUM_MAX
    return num


def vector_similarity(x: list[float], y: list[float]) -> float:
    """
    Returns the similarity between two vectors.

    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))


def order_document_sections_by_query_similarity(query: str, embeddings) -> list[(float, (str, str))]:
    """
    Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    to find the most relevant sections. 

    Return the list of document sections, sorted by relevance in descending order.
    """
    query_embedding = get_embedding(query)
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in enumerate(embeddings)
    ], reverse=True, key=lambda x: x[0])
    return document_similarities


def ask(question: str, embeddings, sources):
    ordered_candidates = order_document_sections_by_query_similarity(
        question, embeddings)
    ctx = u""
    for candi in ordered_candidates:
        next = ctx + u"\n" + sources[candi[1]]
        if len(next) > CONTEXT_TOKEN_LIMIT:
            logging.info(
                f"Exceeded CONTEXT_TOKEN_LIMIT at candidate index {candi[1]}")
            break
        ctx = next
    if len(ctx) == 0:
        return u""

    prompt = u"".join([
        u"Answer the question base on the context, answer in the same language of question\n\n"
        u"Context:" + ctx + u"\n\n"
        u"Question:" + question + u"\n\n"
        u"Answer:"
    ])
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    return completion.choices[0].message.content
