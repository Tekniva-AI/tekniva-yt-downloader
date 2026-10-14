"""Select yt-dlp's network handler without forcing browser impersonation."""
import yt_dlp

ENGINES = ('curl_cffi', 'aria2')


def prefer_curl(handler, request):
    return 1000 if handler.RH_KEY == 'CurlCFFI' else 0


def create_downloader(options):
    downloader = yt_dlp.YoutubeDL(options)
    engine = options.get('tekniva_engine', 'curl_cffi')
    if engine == 'curl_cffi':
        try:
            director = downloader._request_director
            if 'CurlCFFI' not in director.handlers:
                raise RuntimeError('curl_cffi component is missing. Reinstall the application or its requirements.')
            director.preferences.add(prefer_curl)
        except BaseException:
            downloader.close()
            raise
    if options.get('logger'):
        options['logger'].debug('Transfer engine: ' + engine)
    return downloader
