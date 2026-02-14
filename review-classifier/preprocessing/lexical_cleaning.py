import re
import langid
import nltk
import asyncio
from googletrans import Translator
from textblob import Word
import emoji

# One-time download of the dictionary
nltk.download('words', quiet=True)
from nltk.corpus import words as nltk_words

class LexicalCleaner:
    def __init__(self):
        self.translator = Translator()
        self.vocabulary = set(w.lower() for w in nltk_words.words())
    
    async def translate(self, text: str) -> str:
        result = await self.translator.translate(text, dest="en")
        return result.text

    def clean(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower() # normalize lowercase
        # Remove URLs and HTML tags if any
        text = re.sub(r'https?://\S+|www\.\S+', '', text) 
        text = re.sub(r'<.*?>', '', text)
        # De-elongation of characters to maximum 2 similar neighboring characters
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)
        # Emoji verbalization
        text = emoji.demojize(text)
        text = re.sub(r':([a-z_]+):', r'[\1] ', text)
        text = text.replace("_", " ")
        # Strip excessive whitespace and repeated punctuations
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'([!?.]){2,}', r'\1', text) # ??? -> ?
        # Clean unicode junks and malformed characters
        text = text.encode("ascii", "ignore").decode()
        # Language detection and translation using langid and google translate
        try:
            lang, _ = langid.classify(text)
            if lang != "en":
                text = asyncio.run(self.translate_text(text))
        except Exception:
            pass
        # Spelling correction using N-gram language model (TextBlob)
        words = text.split()
        corrected_words = []
        for w in words:
            prefix = re.match(r'^\W*', w).group()
            suffix = re.match(r'.*?(\W*)$', w).group(1)
            core = w[len(prefix):len(w)-len(suffix)]
            if not core:
                if w.startswith('[') and w.endswith(']'):
                    corrected_words.append(w)
                continue    
            if core in self.vocabulary:
                corrected_words.append(w)
                continue
            word_obj = Word(core)
            suggestions = word_obj.spellcheck()
            best_guess, confidence = suggestions[0]
            if confidence > 0.7:
                corrected_words.append(prefix + best_guess + suffix)
            else:
                corrected_words.append(w)
        text = " ".join([w for w in corrected_words if w])
        return re.sub(r'\s+', ' ', text).strip()

# # Test script
# cleaner = LexicalCleaner()
# print(cleaner.clean("The pizza was greattt!! 🍕🔥"))
# print(cleaner.clean("Sooo happppyyyy!!! 😄🎉"))
# print(cleaner.clean("Check this out: https://example.com <b>amazing</b>!!"))
# print(cleaner.clean("La pizza était délicieuse 🍕"))
# print(cleaner.clean("Ths sentnce has speling erors."))
# print(cleaner.clean("He is not happy with this product."))
# print(cleaner.clean("Wait..... what???   Really!!!"))