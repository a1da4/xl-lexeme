import argparse
import logging
import os
import pickle
import torch

from tqdm import tqdm
from typing import List

from WordTransformer import WordTransformer, InputExample


def collect_usage(target_word: str, file_path: str) -> List[str]:
    """ obtain usages that target word occurs
    :param target_word: str, target word
    :param file_path: str, path to target corpus
    :return: usages: List[str], list of usages(sentences)
    """
    usages = []
    with open(file_path) as fp:
        for line in fp:
            sentence = line.strip()
            words = sentence.split()
            if target_word in set(words):
                usages.append(sentence)
    return usages


def make_batch(usages: List[str], batch_size: int) -> List[List[str]]:
    """
    :param usages: List[str], list of sentences
    :param batch_size: int, batch_size
    :return: samples: List[List[str]]
    """
    sorted_sentence = sorted(usages, key=lambda x: len(x.split()))
    samples = [
        sorted_sentence[i : i + batch_size]
        if i + batch_size < len(sorted_sentence)
        else sorted_sentence[i:]
        for i in range(0, len(sorted_sentence), batch_size)
    ]
    return samples


def find_positions_multiple(text: str, target: str) -> List[List[int]]:
    """ find positions [start, end] of target word in the sentence
    :param text: str, sentence
    :param target: str, target word
    :return: positions: List[List[int]], start and end
    """
    words = text.split()
    logging.debug(f"[find_positions_multiple] words: {words}")
    positions = [id for id in range(len(words)) if words[id] == target]
    logging.debug(f"[find_positions_multiple] positions: {positions}")

    target_positions = []
    for position in positions:
        words_left = [len(words[i]) for i in range(position)]
        start = sum(words_left) + len(words_left)
        logging.debug(f"[find_positions_multiple] - start: {start}")
        end = start + len(target)
        logging.debug(f"[find_positions_multiple] - end: {end}")
        target_positions.append([start, end])
    return target_positions


def main(args) -> None:
    os.makedirs("../../results", exist_ok=True)
    logging.basicConfig(filename="../../results/wordvec_from_lexeme_debug.log", format="%(asctime)s %(message)s", level=logging.DEBUG)
    logging.info(f"[main] args: {args}")

    logging.info("[main] 1. load model...")
    model = WordTransformer('pierluigic/xl-lexeme')
    model.to("cpu")

    logging.info("[main] 2. obtain target words...")
    target_words = []
    with open(args.target_words_list) as fp:
        for line in fp:
            target_word = line.strip()
            target_words.append(target_word)

    logging.info("[main] 3. obtain target vectors...")
    word2vec = {}
    for target_word in tqdm(target_words):
        word2vec[target_word] = []
        target_sentences = collect_usage(target_word, args.file_path)
        logging.debug(f"[main] - {target_word}: {len(target_sentences)} sents")

        batch_size = 16
        examples = []
        for sentence in tqdm(target_sentences, desc=f"[obtain {target_word}'s vectors...]"):
            all_positions = find_positions_multiple(sentence, target_word)
            for positions in all_positions:
                #examples = InputExample(texts=sentence, positions=positions)
                example = InputExample(texts=sentence, positions=positions)
                examples.append(example)
                if len(examples) >= batch_size:
                    target_vectors = model.encode(examples, show_progress_bar=False)
                    word2vec[target_word].extend(list(target_vectors))
                    examples = []
        if len(examples) >= 0:
            target_vectors = model.encode(examples, show_progress_bar=False)
            word2vec[target_word].extend(list(target_vectors))
            examples = []

        logging.debug(f"[main]   - {len(word2vec[target_word])} items")
    
    pickle.dump(word2vec, open(f"../../results/lexeme_{args.output_name}_word2vec.pkl", "wb"))

    logging.info("[main] finished")



def cli_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file_path", help="path of corpus")
    parser.add_argument("-l", "--target_words_list", help="target word list")
    parser.add_argument("-o", "--output_name")
    args = parser.parse_args()
    main(args)


if __name__ == "__main__":
    cli_main()
