from pysle import isletool
import regex as re
from nltk.stem.snowball import SnowballStemmer


stemmer = SnowballStemmer(language='english')
isleDict = isletool.LexicalTool('ISLEdict.txt')
standard_mapping = {
	"ɹ": "r",
	"u": "uː",
	"i": "iː",
	"iɹ": "ɪə",
	"ɛɹ": "ɛː",
	'ɾ': 't',
	'ɵ': 'θ',
	
	"ɝ": "əː",
	"ɚ": "ə",
	"ɚɹ": "əː",
	
	"ɔ": "ɔː",
	"ɔn": "ɒn",
	"ɔi": "ɔɪ",
	"ɔɹ": "ɔː",
	
	"ɑ": "ɒ",
	"ɑɹ": "ɑː",
	"ɑɪ": "ɑɪ",
	
	"ei": "eɪ",
}

# from https://simple.wikipedia.org/wiki/Vowel
vowels = ['ɪ', 'iː',
		  'ɛ', 'ɛː', 'æ',
		  'ʊ', 'uː', 'ʌ',
		  'ə', 'əː',
		  'ɒ', 'ɔː',
		  'ɑː',
		  'eɪ','oʊ', 'ɑɪ', 'aʊ', 'ɔɪ', 'ɪə']

# from https://en.wikipedia.org/wiki/English_phonology#Consonants
consonants = ['p', 'b',
			  't', 'd',
			  'k', 'g',
			  'tʃ','dʒ',
			  'f', 'v',
			  'θ', 'ð',
			  's', 'z',
			  'ʃ', 'ʒ',
			  'x',
			  'h', 'm',
				   'n',
				   'ŋ',
				   'j',
				   'w',
				   'r',
				   'l',
				   'l̩',
				   'm̩',
				   'n̩']

phonemes = set(vowels + consonants)


def normalize(word):
	word = word.lower()
	word = re.sub("^[^a-zA-Z0-9]*", "", word)
	word = re.sub("[^a-zA-Z0-9]*$", "", word)
	return word


def normalize_ipa(ipa):
	ipa = re.sub("[ˈˌ]", "", ipa)
	return ipa


def transcribe(word, original=False):
	word = normalize(word)
	if word not in isleDict.data:
		return []
	ipas = []
	for ipa, _, _ in isleDict.lookup(word)[0]:
		if original:
			res += ["".join(["".join(morpheme) for morpheme in ipa])]
		else:
			standard_ipa = []
			for morpheme in ipa:
				morpheme = "".join(morpheme)
				i, standard_morpheme = 0, ""
				while i < len(morpheme):
					if morpheme[i:i+2] in standard_mapping:
						phoneme = standard_mapping[morpheme[i:i+2]]
						i += 2
					elif morpheme[i:i+1] in standard_mapping:
						phoneme = standard_mapping[morpheme[i:i+1]]
						i += 1
					else:
						phoneme = morpheme[i]
						i += 1
					standard_morpheme += phoneme
				standard_ipa += [standard_morpheme]
			ipas += [standard_ipa]
	return ipas


def break_into_phones(ipa):
	res = []
	i = 0
	while i < len(ipa):
		if ipa[i] in "ˈˌ":
			i += 1
			continue
		if ipa[i:i+2] in phonemes:
			res += [ipa[i:i+2]]
			i += 2
		elif ipa[i] in phonemes:
			res += [ipa[i]]
			i += 1
		else:
			print(ipa, ipa[i:])
			raise("not found")
	return res


def stem(word, original=False):
	word = normalize(word)
	root = stemmer.stem(word)
	if original:
		return root
	res = ""
	for a,b in zip(root, word):
		if a != b:
			break
		res += a
	return res


def stem_paragraph(paragraph, original=False):
	return [stem(word, original) for word in paragraph.split()]


def transcribe_paragraph(paragraph, original=False):
	return [transcribe(word, original) for word in paragraph.split()]