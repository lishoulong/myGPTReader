from text2vec import SentenceModel, cos_sim, semantic_search
import sys
import os
from embedding import summarize_source
# 将以下路径替换为实际的 "app" 目录路径
path_to_your_app_directory = '/Users/lishoulong/Documents/toutiao/lib/openai/second/myGPTReader/app'
sys.path.insert(0, os.path.abspath(path_to_your_app_directory))
# sys.path.append('..')

embedder = SentenceModel()

# Corpus with example sentences
corpus = [
    '花呗更改绑定银行卡',
    '我什么时候开通了花呗',
    'A man is eating food.',
    'A man is eating a piece of bread.',
    'The girl is carrying a baby.',
    'A man is riding a horse.',
    'A woman is playing violin.',
    'Two men pushed carts through the woods.',
    'A man is riding a white horse on an enclosed ground.',
    'A monkey is playing drums.',
    'A cheetah is running behind its prey.'
]
corpus_embeddings = embedder.encode(corpus)

summarize_source(corpus, corpus_embeddings)
# Query sentences:
# queries = [
#     '如何更换花呗绑定银行卡',
#     'A man is eating pasta.',
#     'Someone in a gorilla costume is playing a set of drums.',
#     'A cheetah chases prey on across a field.']

# for query in queries:
#     query_embedding = embedder.encode(query)
#     hits = semantic_search(query_embedding, corpus_embeddings, top_k=5)
#     print("\n\n======================\n\n")
#     print("Query:", query)
#     print("\nTop 5 most similar sentences in corpus:")
#     hits = hits[0]  # Get the hits for the first query
#     for hit in hits:
#         print(corpus[hit['corpus_id']], "(Score: {:.4f})".format(hit['score']))
