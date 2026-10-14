# curl_cffi bundled library notices

curl_cffi 0.16.0 builds against libcurl-impersonate v2.0.0.
The exact component references are taken from its CMakeLists.txt:
https://github.com/lexiforest/curl-impersonate/blob/v2.0.0/CMakeLists.txt
The Windows wheel uses the upstream Win32 x64 library build:
https://github.com/lexiforest/curl-impersonate/releases/tag/v2.0.0
curl_cffi build definition:
https://github.com/lexiforest/curl_cffi/blob/v0.16.0/scripts/build.py

These license texts are copied without modifications from the corresponding
source tags/commit. zstd is dual licensed; both upstream texts are included.

- curl-impersonate-LICENSE: https://raw.githubusercontent.com/lexiforest/curl-impersonate/v2.0.0/LICENSE
- libcurl-COPYING: https://raw.githubusercontent.com/curl/curl/curl-8_21_0/COPYING
- BoringSSL-LICENSE: https://raw.githubusercontent.com/google/boringssl/156c7b75ae9b8c3b3f847acf264f17594c3859fb/LICENSE
- brotli-LICENSE: https://raw.githubusercontent.com/google/brotli/v1.2.0/LICENSE
- zlib-LICENSE: https://raw.githubusercontent.com/madler/zlib/v1.3.1/LICENSE
- zstd-LICENSE: https://raw.githubusercontent.com/facebook/zstd/v1.5.7/LICENSE
- zstd-COPYING: https://raw.githubusercontent.com/facebook/zstd/v1.5.7/COPYING
- nghttp2-COPYING: https://raw.githubusercontent.com/nghttp2/nghttp2/v1.63.0/COPYING
- ngtcp2-COPYING: https://raw.githubusercontent.com/ngtcp2/ngtcp2/v1.20.0/COPYING
- nghttp3-COPYING: https://raw.githubusercontent.com/ngtcp2/nghttp3/v1.15.0/COPYING
