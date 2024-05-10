import re

def process_captions(transcriptdict: list[dict]):
    preprocess_captions = ""
    for line in transcriptdict:
        preprocess_captions += " " + line['text']
    removed_descriptive = re.sub(
        " [\(\[].*?[\)\]]", "", preprocess_captions)
    output = re.sub(r'\b(\w+) \1\b', r'\1',
                    removed_descriptive, flags=re.IGNORECASE)
    output = output.replace("\n", " ").replace(u'\xa0', u' ')
    output = re.sub(' +', ' ', output)
    return output[1:]

