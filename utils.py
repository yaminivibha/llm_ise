import argparse


def tValue(string) -> float:
    value = float(string)
    if value < 0 or value > 1:
        raise argparse.ArgumentTypeError("t value has to be a float between 0 and 1")
    return value


def rValue(string) -> int:
    value = int(string)
    if value < 1 or value > 4:
        raise argparse.ArgumentTypeError("r value has to be an integer between 1 and 4")
    return value


def kValue(string) -> int:
    value = int(string)
    if value < 1:
        raise argparse.ArgumentTypeError("k value has to be an integer greater than 0")
    return value


def validate_LLM(args, parser) -> None:
    if args.spanbert and args.gpt3:
        raise parser.error("Cannot use both SpanBERT and GPT-3")

    if not args.spanbert and not args.gpt3:
        raise parser.error("Must use either SpanBERT or GPT-3")

    return
