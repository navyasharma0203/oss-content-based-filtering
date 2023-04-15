import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
cors = CORS(app)
# cors = CORS(app, resources={r"/*": {"origins": "*"}})


# CORS error handling

"""Import the dataset"""

df = pd.read_csv('oss_data.csv')

"""Combining the different attributes of the dataset into a single string"""

df['content'] = df['name'].astype(str) + ' ' + df['desc'].astype(str) + ' ' + df['tags'] + ' ' + df['upforgrabs__link'].astype(str)
df['content'] = df['content'].fillna('')
df['content']

"""Tokenize content for Word2Vec"""

df['tokenized_content'] = df['content'].apply(simple_preprocess)
df['tokenized_content']

"""Training the Word2Vec model"""

model = Word2Vec(vector_size=100, window=5, min_count=1, workers=4)
model.build_vocab(df['tokenized_content'])
model.train(df['tokenized_content'], total_examples=model.corpus_count, epochs=10)

"""Function to average word vectors for a text"""

def average_word_vectors(words, model, vocabulary, num_features):
    feature_vector = np.zeros((num_features,), dtype="float64")
    nwords = 0.
    
    for word in words:
        if word in vocabulary: 
            nwords = nwords + 1.
            feature_vector = np.add(feature_vector, model.wv[word])
    
    if nwords:
        feature_vector = np.divide(feature_vector, nwords)
        
    return feature_vector

"""Function to compute average word vectors for all repos"""

def averaged_word_vectorizer(corpus, model, num_features):
    vocabulary = set(model.wv.index_to_key)
    features = [average_word_vectors(tokenized_sentence, model, vocabulary, num_features) for tokenized_sentence in corpus]
    return np.array(features)

"""Compute average word vectors for all repos"""

w2v_feature_array = averaged_word_vectorizer(corpus=df['tokenized_content'], model=model, num_features=100)

@app.route('/similar_repos', methods=['POST'])
def get_similar_repos():
    user_oss = request.json['query']
    oss_index = df[df['name'] == user_oss].index[0]
    user_oss_vector = w2v_feature_array[oss_index].reshape(1, -1)
    similarity_scores = cosine_similarity(user_oss_vector, w2v_feature_array)

    similar_repos = list(enumerate(similarity_scores[0]))
    sorted_similar_repos = sorted(similar_repos, key=lambda x: x[1], reverse=True)[1:11]
    result = [{'name': df.loc[i, 'name'], 'similarity_score': score,'desc':df.loc[i,'desc'], 'tags':df.loc[i,'tags'], 'link':df.loc[i,'upforgrabs__link']} for i, score in sorted_similar_repos]

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
