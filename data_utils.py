import regex as re

def clean(text):
	text = re.sub("[“”]", "\"", text)
	text = re.sub("[‘’]", "'", text)
	text = re.sub("[-—]", " ", text)
	text = re.sub("\s+", " ", text)
	text = re.sub("\s*(\.){3}\s*([a-zA-Z])", r"… \2", text)
	text = re.sub("\s*…\s*([a-zA-Z])", r"… \1", text)
	return text.strip()

def break_into_sents(paragraph):
	sentences = re.split("(\..*?\s)", paragraph)
	sentences = [(body + limitter).strip() for body, limitter in zip(sentences[0::2], sentences[1::2] + [""])]
	return sentences

def break_into_short_parags(paragraph, break_length):
	if len(paragraph.split()) <= break_length:
		return [paragraph]
	
	sentences = break_into_sents(paragraph)
	if len(sentences) < 2:
		return [paragraph]
	
	paragraphs = []
	curr_parag = []
	curr_len = 0
	for sent in sentences:
		curr_parag += [sent]
		curr_len += len(sent.split())
		
		if curr_len >= break_length:
			paragraphs += [" ".join(curr_parag)]
			curr_parag = []
			curr_len = 0
			
	if curr_parag:
		paragraphs += [" ".join(curr_parag)]
		
	return paragraphs