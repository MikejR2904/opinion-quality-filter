import re
from functools import lru_cache
from datasketch import MinHash, MinHashLSH
from textblob import TextBlob, Word

# One-time download the required setups for Blob
import nltk
nltk.download('punkt_tab') # handles sentence or word splitting
nltk.download('averaged_perceptron_tagger_eng', quiet=True) # handles tags
nltk.download('wordnet') # get hypernyms of word

# All Google Maps categories can be found at https://pleper.com/index.php?do=tools&sdo=gmb_categories
# We process only for common business categories.
CATEGORY_ASPECTS = {
    "restaurant": [
        "food", "menu", "taste", "delicious", "flavor", "fresh", "dish", "cuisine", "ingredients",
        "price", "cost", "bill", "value", "service", "staff", "waiter", "server", "friendly",
        "table", "waiting", "reservation", "booking", "ambience", "atmosphere", "vibe", "decor",
        "clean", "hygiene", "facility", "restroom"
    ],
    "cafe": [
        "coffee", "espresso", "latte", "brew", "drink", "beverage", "tea", "dessert", "pastry", "cake",
        "wifi", "internet", "power outlet", "work", "ambience", "vibe", "music", "seat", "table",
        "price", "affordable", "service", "staff"
    ],
    "hotel": [
        "room", "bed", "pillow", "sleep", "bathroom", "shower", "amenities", "clean", "tidy", "housekeeping",
        "staff", "reception", "concierge", "check-in", "location", "view", "nearby", "walking",
        "facility", "pool", "gym", "elevator", "parking", "breakfast", "buffet", "service", "price"
    ],
    "bar": [
        "drink", "cocktail", "beer", "wine", "alcohol", "liquor", "menu", "music", "dj", "band",
        "crowd", "busy", "lively", "price", "happy hour", "service", "bartender", "staff",
        "ambience", "atmosphere", "vibe", "decor", "lighting"
    ],
    "gym": [
        "equipment", "machine", "weights", "cardio", "clean", "locker", "shower", "hygiene",
        "trainer", "coach", "staff", "facility", "pool", "sauna", "crowd", "busy", "peak",
        "price", "membership", "subscription", "class", "workout", "session", "service"
    ],
    "supermarket": [
        "product", "item", "grocery", "stock", "variety", "selection", "inventory", "price", "cheap",
        "freshness", "produce", "fruit", "vegetable", "meat", "staff", "cashier", "queue", "line",
        "checkout", "location", "parking", "clean", "aisle"
    ],
    "park": [
        "nature", "tree", "grass", "trail", "path", "clean", "litter", "maintenance", "facility",
        "bench", "playground", "toilet", "crowd", "quiet", "peaceful", "ambience", "atmosphere",
        "safety", "security", "lighting", "location", "parking", "view"
    ],
    "museum": [
        "exhibit", "collection", "display", "art", "history", "gallery", "staff", "guide", "info",
        "facility", "elevator", "cafe", "shop", "crowd", "tourist", "noise", "price", "admission",
        "ticket", "ambience", "lighting", "atmosphere", "location", "artifact", "admission", "fee"
    ],
    "shopping_mall": [
        "store", "brand", "shop", "boutique", "variety", "selection", "price", "sale", "food court",
        "facility", "restroom", "elevator", "escalator", "parking", "crowd", "busy", "vibe",
        "ambience", "decor", "location", "accessible"
    ],
    "cinema": [
        "movie", "film", "screening", "seat", "comfort", "legroom", "sound", "audio", "screen",
        "visual", "imax", "3d", "price", "ticket", "popcorn", "snack", "concession", "crowd",
        "facility", "clean", "staff"
    ],
    "airport": [
        "terminal", "gate", "lounge", "facility", "duty free", "shop", "restaurant", "staff",
        "customs", "immigration", "queue", "wait", "line", "security", "check-in", "location",
        "transport", "shuttle", "clean", "service", "ambience", "signage"
    ],
    "school": [
        "teacher", "instructor", "faculty", "staff", "admin", "principal", "facility", "classroom",
        "lab", "library", "playground", "location", "campus", "class", "lesson", "course",
        "clean", "environment", "ambience", "atmosphere", "service", "school fee", "hall"
    ]
}

OVERLAP_THRESHOLD = 0.85

class SemanticDeduplicator:
    def __init__(self, threshold: int = 0.85, num_perm: int = 128, k: int = 5):
        self.threshold = threshold
        self.num_perm = num_perm
        self.k = k

    def _get_shingles(self, text: str, k: int = 5): # creates k-gram shingles
        if len(text) < k:
            return {text}
        return set(text[i:i+k] for i in range(len(text)-k+1))
    
    def _word_overlap(self, a: str, b: str) -> float: # calculate Szymkiewicz–Simpson (or overlap) coefficient
        word_a, word_b = set(a.split()), set(b.split())
        shorter = word_a if len(word_a) <= len(word_b) else word_b
        longer = word_a if len(word_a) > len(word_b) else word_b
        if not shorter:
            return 0.0
        return len(shorter & longer) / len(shorter) # overlap(a,b) = len(A and B)/min(len(A), len(B))
    
    @lru_cache(maxsize=2000)
    def _calculate_aspect_score(self, text: str, category: str) -> float:
        if category not in CATEGORY_ASPECTS:
            return len(text.split()) * 0.1
        blob = TextBlob(text)
        text_lower = text.lower()
        unique_aspects = set()
        total_aspect_mentions = 0
        keywords = CATEGORY_ASPECTS[category]
        for kw in keywords: # explicit keyword matching
            matches = re.findall(r'\b' + re.escape(kw) + r'\b', text_lower)
            if matches:
                unique_aspects.add(kw)
                total_aspect_mentions += len(matches)
        # POS Tagging; zero-shot hypernym mapping to the listed subcategories
        for word, pos in blob.tags:
            clean_word = word.lower()
            if pos in ['NN', 'NNS'] and clean_word not in unique_aspects:
                synsets = Word(clean_word).get_synsets(pos='n')
                mapped = False
                for syn in synsets:
                    for path in syn.hypernym_paths():
                        for ancestor in path:
                            ancestor_name = ancestor.name().split('.')[0]
                            if ancestor_name in keywords:
                                unique_aspects.add(clean_word)
                                total_aspect_mentions += 1
                                mapped = True
                                break
                        if mapped: break
                    if mapped: break
        score = len(unique_aspects) + (0.5 * total_aspect_mentions)
        return score

    def deduplicate(self, reviews: list, category: str) -> list:
        if not reviews:
            return []
        lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        minhashes = {}
        # Generate signatures and insert to LSH (locality sensitive hashing)
        for i, text in enumerate(reviews):
            m = MinHash(num_perm=self.num_perm)
            for shingle in self._get_shingles(text, k=self.k):
                m.update(shingle.encode('utf-8'))
            lsh.insert(f"idx_{i}", m)
            minhashes[i] = m
        # Cluster duplicates or near-identical reviews
        ## IDEA: Jaccard (MinHash) looks at the total intersection over the total union
        ##       We need to also look at the intersection over the size of the smaller set using overlap coeff. 
        clusters = []
        visited = set()
        for i in range(len(reviews)):
            if i in visited:
                continue
            candidates = lsh.query(minhashes[i])
            cluster_indices = [int(name.split('_')[1]) for name in candidates]
            # Second-pass filter to verify actual duplicates or just shorter subsets
            for j in range(len(reviews)):
                if j not in cluster_indices and j not in visited:
                    if self._word_overlap(reviews[i], reviews[j]) > OVERLAP_THRESHOLD:
                        cluster_indices.append(j)
            new_cluster = [idx for idx in cluster_indices if idx not in visited]
            if new_cluster:
                clusters.append(new_cluster)
                visited.update(new_cluster)
        # Representative selection
        final_reviews = []
        for cluster in clusters:
            representative_idx = max(cluster, key=lambda idx: (self._calculate_aspect_score(reviews[idx], category), len(reviews[idx])))
            if self._calculate_aspect_score(reviews[representative_idx], category) > 0:
                final_reviews.append(reviews[representative_idx])
        return final_reviews
    
# # Test script
# from lexical_cleaning import LexicalCleaner
# cleaner = LexicalCleaner()
# deduplicator = SemanticDeduplicator(threshold=0.7, k=3)

# raw_reviews = [
#     # Cluster 1: The "Near-Duplicate" (Should merge)
#     "The ribeye was succulent and the server was so helpful.",           # Review A
#     "The ribeye was succulent and the server was so helpful! Amazing!",   # Review B (Near-dup of A)
#     # Cluster 2: Same category, but different semantic content (Should NOT merge)
#     "The prices were astronomical but the atmosphere was chic.",         # Review C (Logistics/Ambience)
#     # Cluster 3: Industry-specific nouns not in your list (Tests WordNet mapping)
#     "The linguine was al dente and the lasagna was flavorful.",          # Review D (Specific dishes)
#     # Cluster 4: Junk (Should have a near-zero score)
#     "Whoa... okay then."                                                 # Review E
# ]

# category = "restaurant"
# print(f"--- Processing {len(raw_reviews)} reviews for category: {category} ---\n")
# # We clean first so MinHash works on normalized text
# cleaned_reviews = [cleaner.clean(r) for r in raw_reviews]
# for i, r in enumerate(cleaned_reviews):
#     score = deduplicator._calculate_aspect_score(r, category)
#     print(f"Cleaned [{i}]: {r}")
#     print(f"Aspect Score: {score}\n")
# # This will group Review A and B, then pick Review B because of the higher score
# final_reviews = deduplicator.deduplicate(cleaned_reviews, category)
# print("--- Final Result after Deduplication ---")
# for r in final_reviews:
#     print(f"Result: {r}")