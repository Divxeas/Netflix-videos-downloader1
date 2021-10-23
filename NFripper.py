import argparse, json, os, logging
from configs.config import tool
from helpers.proxy_environ import proxy_env
from datetime import datetime
from services.netflix import netflix

script_name = "NF Ripper"
script_ver = "2.0.1.0"

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=f">>> {script_name} {script_ver} <<<")
    parser.add_argument("content", nargs="?", help="Content URL or ID")
    parser.add_argument("-q", dest="customquality", nargs=1, help="For configure quality of video.", default=[])
    parser.add_argument("-o", dest="output", help="download all assets to directory provided.")
    parser.add_argument("-f", dest="output_folder", help="force mux .mkv files to directory provided", action="store", default=None)
    parser.add_argument("--nv", dest="novideo", help="dont download video", action="store_true")
    parser.add_argument("--na", dest="noaudio", help="dont download audio", action="store_true")
    parser.add_argument("--ns", dest="nosubs", help="dont download subs", action="store_true")
    parser.add_argument("-e", dest="episodeStart", help="it will start downloading the season from that episode.", default=None)
    parser.add_argument("-s", dest="season", help="it will start downloading the from that season.", default=None)
    parser.add_argument("--keep", dest="keep", help="well keep all files after mux, by default all erased.", action="store_true")
    parser.add_argument("--only-2ch-audio", dest="only_2ch_audio", help="to force get only eac3 2.0 Ch audios.", action="store_true")
    parser.add_argument("--alang", dest="audiolang", nargs="*", help="download only selected audio languages", default=[],)
    parser.add_argument("--AD", '--adlang', dest="AD", nargs="*", help="download only selected audio languages", default=[],)
    parser.add_argument("--slang", dest="sublang", nargs="*", help="download only selected subtitle languages", default=[],)
    parser.add_argument("--flang", dest="forcedlang", nargs="*", help="download only selected forced subtitle languages", default=[],)
    parser.add_argument('-t', "--title", dest="titlecustom", nargs=1, help="Customize the title of the show", default=[],)
    parser.add_argument('-p', "--prompt", dest="prompt", help="will Enable the yes/no prompt when URLs are grabbed.", action="store_true")
    parser.add_argument('-keys', "--license", dest="license", help="print all profiles keys and exit.", action="store_true")   
    parser.add_argument("--audio-bitrate", dest="custom_audio_bitrate", nargs=1, help="For configure bitrate of audio.", default=[])
    parser.add_argument("--aformat-2ch","--audio-format-2ch", dest="aformat_2ch",nargs=1, help="For configure format of audio.", default=[],)
    parser.add_argument("--aformat-51ch","--audio-format-51ch", dest="aformat_51ch",nargs=1, help="For configure format of audio.", default=[],)
    parser.add_argument("--android-login", dest="android_login", help="will log netflix using android api and save cookies nd build.", action="store_true",)
    parser.add_argument("--search", action="store", dest="search", help="download using netflix search for the movie/show.", default=0,)
    parser.add_argument("--hevc", dest="hevc", help="will return HEVC profile", action="store_true")
    parser.add_argument("--hdr", dest="hdr", help="will return HDR profile", action="store_true")    
    parser.add_argument("--high", dest="video_high", help="return MSL High Video manifest for hpl videos, usually small size low bitrate.", action="store_true",)
    parser.add_argument("--main", dest="video_main", help="return MSL Main Video manifest for mpl videos, usually Big size High bitrate.", action="store_true",) 
    parser.add_argument("--check", dest="check", help="hpl vs mpl.", action="store_true",)     
    parser.add_argument("--all-audios", dest="allaudios", help="all download audios of the movie/show", action="store_true",)
    parser.add_argument("--all-forced", dest="allforcedlang", help="all download forced subs of the movie/show", action="store_true",)
    parser.add_argument("--no-aria2c", dest="noaria2c", help="not use aria2c for download, will use python downloader.", action="store_true",)
    
    # PROXY
    parser.add_argument("--nrd", action="store", dest="nordvpn", help="add country for nordvpn proxies.", default=0,)
    parser.add_argument("--prv", action="store", dest="privtvpn", help="add country for privtvpn proxies.", default=0,)
    parser.add_argument("--no-dl-proxy", dest="no_download_proxy", help="do not use proxy will downloading files", action="store_true", default=False,)
   
   # PACK
    parser.add_argument("--gr", dest="muxer_group", help="add group name to use that will override the one in config", action="store", default=None)
    parser.add_argument("--upload", dest="upload_ftp", help="upload the release after packing", action="store_true", default=None)
    parser.add_argument("--pack", dest="muxer_pack", help="pack the release", action="store_true", default=None)
    parser.add_argument("--confirm", dest="confirm_upload", help="ask confirming before upload the packed release", action="store_true", default=None)
    parser.add_argument("--imdb", dest="muxer_imdb", help="add imdb for the title for packing", action="store", default=None)
    parser.add_argument("--scheme", dest="muxer_scheme", help="set muxer scheme name", default=None)
    # cleaner
    parser.add_argument("--clean-add", dest="clean_add", nargs="*", help="add more extension of files to be deleted", default=[],)
    parser.add_argument("--clean-exclude", dest="clean_exclude", nargs="*", help="add more extension of files to not be deleted", default=[],)
    parser.add_argument("--log-level", default="info", dest="log_level", choices=["debug", "info", "error", "warning"], help="choose level")
    parser.add_argument("--log-file", dest="log_file", help="set log file for debug", default=None)
    args = parser.parse_args()

    start = datetime.now()

    if args.log_file:
        logging.basicConfig(
            filename=args.log_file,
            format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %I:%M:%S %p",
            level=logging.DEBUG,
        )
    
    else:
        if args.log_level.lower() == "info":
            logging.basicConfig(format="%(message)s", level=logging.INFO)
        elif args.log_level.lower() == "debug":
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %I:%M:%S %p",
                level=logging.DEBUG,
            )
        elif args.log_level.lower() == "warning":
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %I:%M:%S %p",
                level=logging.WARNING,
            )
        elif args.log_level.lower() == "error":
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %I:%M:%S %p",
                level=logging.ERROR,
            )
    
    logging.getLogger(__name__)

    group = {
        "UPLOAD": args.upload_ftp,
        "IMDB": args.muxer_imdb,
        "SCHEME": args.muxer_scheme,
        "PACK": args.muxer_pack,
        "GROUP": args.muxer_group,
        "CONFIRM": args.confirm_upload,
        "EXTRA_FOLDER": args.output_folder,
    }
    
    # ~ commands
    proxy, ip = proxy_env(args).Load()
    commands = {"aria2c_extra_commands": proxy, "group": group}
    logging.debug(commands)

    if args.license:
        args.prompt = False

    l = "\n__________________________\n"
    print(
        f"\n--  {script_name}  --{l}\nVERSION: {script_ver}{l}\nIP: {ip}{l}"
    )

    netflix_ = netflix(args, commands)
    netflix_.main_netflix()

    print(
        "\nNFripper took {} Sec".format(
            int(float((datetime.now() - start).total_seconds()))
        )
    )  # total seconds
