import argparse
from .subtitles import render

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source_video',required=True)
    parser.add_argument('--job',required=True)
    parser.add_argument('--home',required=True)
    args=parser.parse_args()
    render(args.job,args.home)
