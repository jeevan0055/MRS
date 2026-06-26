import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
import re
from typing import List, Tuple, Dict


class MovieRecommender:
    def __init__(self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame, tags_df: pd.DataFrame = None):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.tags_df = tags_df

        self._prepare_data()
        self._build_content_based_model()
        self._build_collaborative_model()

    def _prepare_data(self):
        # Extract year from title
        def extract_year(title):
            match = re.search(r"\((\d{4})\)", title)
            return int(match.group(1)) if match else None

        self.movies_df["year"] = self.movies_df["title"].apply(extract_year)
        self.movies_df["title"] = self.movies_df["title"].str.replace(r"\s*\(\d{4}\)", "", regex=True)

        # Process tags
        if self.tags_df is not None:
            tag_agg = self.tags_df.groupby("movieId")["tag"].apply(lambda x: " ".join(x.astype(str))).reset_index()
            tag_agg.columns = ["movieId", "tags"]
            self.movies_df = self.movies_df.merge(tag_agg, on="movieId", how="left")
            self.movies_df["tags"] = self.movies_df["tags"].fillna("")
        else:
            self.movies_df["tags"] = ""

        # Combine genres and tags
        self.movies_df["content"] = (
            self.movies_df["genres"].str.replace("|", " ") + " " + self.movies_df["tags"]
        )

    def _build_content_based_model(self):
        self.tfidf = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(self.movies_df["content"])
        self.content_similarity = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)

    def _build_collaborative_model(self):
        # Create user-item matrix
        user_item_matrix = self.ratings_df.pivot(
            index="userId", columns="movieId", values="rating"
        ).fillna(0)

        self.user_item_matrix = csr_matrix(user_item_matrix.values)
        self.user_ids = user_item_matrix.index.tolist()
        self.movie_ids = user_item_matrix.columns.tolist()
        self.movie_id_to_idx = {movie_id: i for i, movie_id in enumerate(self.movie_ids)}
        self.idx_to_movie_id = {i: movie_id for i, movie_id in enumerate(self.movie_ids)}

        # KNN model
        self.knn_model = NearestNeighbors(metric="cosine", algorithm="brute")
        self.knn_model.fit(self.user_item_matrix.T)

    def get_content_based_recommendations(
        self, movie_id: int, top_n: int = 10
    ) -> List[Tuple[int, float, str]]:

        if movie_id not in self.movies_df["movieId"].values:
            return []

        idx = self.movies_df[self.movies_df["movieId"] == movie_id].index[0]

        sim_scores = list(enumerate(self.content_similarity[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1: top_n + 1]

        recommendations = []

        for i, score in sim_scores:
            rec_movie_id = self.movies_df.iloc[i]["movieId"]
            explanation = "Similar in genres and tags to this movie"
            recommendations.append((rec_movie_id, score, explanation))

        return recommendations

    def get_collaborative_recommendations(
        self, user_id: int, top_n: int = 10
    ) -> List[Tuple[int, float, str]]:

        if user_id not in self.user_ids:
            return []

        user_idx = self.user_ids.index(user_id)
        user_ratings = self.user_item_matrix[user_idx].toarray().flatten()

        # Find movies user hasn't rated
        unrated_movie_indices = np.where(user_ratings == 0)[0]

        if len(unrated_movie_indices) == 0:
            return []

        recommendations = []

        for movie_idx in unrated_movie_indices:

            movie_id = self.idx_to_movie_id[movie_idx]

            distances, indices = self.knn_model.kneighbors(
                self.user_item_matrix.T[movie_idx].reshape(1, -1),
                n_neighbors=5
            )

            neighbor_indices = indices.flatten()

            ratings = [
                user_ratings[i]
                for i in neighbor_indices
                if user_ratings[i] > 0
            ]

            if ratings:
                avg_rating = np.mean(ratings)

                if avg_rating > 0:
                    recommendations.append(
                        (
                            movie_id,
                            avg_rating,
                            "Users with similar preferences also liked this"
                        )
                    )

        recommendations = sorted(
            recommendations,
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        return recommendations

    def get_hybrid_recommendations(
        self,
        user_id: int,
        top_n: int = 10,
        content_weight: float = 0.5,
        collaborative_weight: float = 0.5,
    ) -> List[Tuple[int, float, str]]:

        user_rated_movies = self.ratings_df[
            self.ratings_df["userId"] == user_id
        ]

        if user_rated_movies.empty:
            return self.get_popularity_based_recommendations(top_n)

        high_rated_movies = user_rated_movies[
            user_rated_movies["rating"] >= 4.0
        ]["movieId"].tolist()

        content_recs = {}

        for movie_id in high_rated_movies:
            recs = self.get_content_based_recommendations(movie_id, top_n=5)

            for rec_movie_id, score, exp in recs:

                if rec_movie_id not in user_rated_movies["movieId"].values:

                    if rec_movie_id in content_recs:
                        content_recs[rec_movie_id]["score"] += score
                        content_recs[rec_movie_id]["explanations"].append(exp)
                    else:
                        content_recs[rec_movie_id] = {
                            "score": score,
                            "explanations": [exp]
                        }

        collab_recs = {}

        collab_list = self.get_collaborative_recommendations(
            user_id,
            top_n=20
        )

        for rec_movie_id, score, exp in collab_list:

            if rec_movie_id not in user_rated_movies["movieId"].values:
                collab_recs[rec_movie_id] = {
                    "score": score,
                    "explanations": [exp]
                }

        combined = {}

        for movie_id in set(content_recs.keys()).union(
            set(collab_recs.keys())
        ):

            total_score = 0
            explanations = []

            if movie_id in content_recs:
                total_score += (
                    content_recs[movie_id]["score"] * content_weight
                )
                explanations.extend(
                    content_recs[movie_id]["explanations"]
                )

            if movie_id in collab_recs:
                total_score += (
                    collab_recs[movie_id]["score"]
                    * collaborative_weight
                    / 5
                )

                explanations.extend(
                    collab_recs[movie_id]["explanations"]
                )

            combined[movie_id] = {
                "score": total_score,
                "explanations": list(set(explanations))
            }

        sorted_recs = sorted(
            combined.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )[:top_n]

        final_recs = []

        for movie_id, data in sorted_recs:

            explanation = " and ".join(data["explanations"])

            if high_rated_movies:
                top_movie = self.movies_df[
                    self.movies_df["movieId"] == high_rated_movies[0]
                ]["title"].iloc[0]

                explanation = (
                    f"Recommended because you rated "
                    f"{top_movie} highly, {explanation}"
                )

            final_recs.append(
                (
                    movie_id,
                    data["score"],
                    explanation
                )
            )

        return final_recs

    def get_popularity_based_recommendations(
        self,
        top_n: int = 10
    ) -> List[Tuple[int, float, str]]:

        movie_stats = self.ratings_df.groupby("movieId").agg(
            avg_rating=("rating", "mean"),
            num_ratings=("rating", "count")
        ).reset_index()

        movie_stats["score"] = (
            movie_stats["num_ratings"] / movie_stats["num_ratings"].max() * 0.5
            + movie_stats["avg_rating"] / 5 * 0.5
        )

        movie_stats = movie_stats.sort_values(
            "score",
            ascending=False
        ).head(top_n)

        return [
            (
                row["movieId"],
                row["score"],
                "Trending and popular among all users"
            )
            for _, row in movie_stats.iterrows()
        ]

    def get_similar_movies(
        self,
        movie_id: int,
        top_n: int = 10
    ) -> List[Tuple[int, float, str]]:

        return self.get_content_based_recommendations(
            movie_id,
            top_n
        )