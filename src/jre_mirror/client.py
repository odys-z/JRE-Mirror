# """
# Credits: [jyksnw/install-jdk](https://github.com/jyksnw/install-jdk)
# install-jdk/jdk/client/client.py
# License: MIT
# """
# import shutil
# import tempfile
# from collections.abc import Iterable
# from os import path
# from typing import Callable
# from typing import List
# from typing import Optional
# from typing import Union
# from urllib import request
# from urllib.parse import urlsplit
#
# import requests
#
# from enums import Architecture
# from enums import Implementation
# from enums import JvmImpl
# from enums import OperatingSystem
# from enums import Vendor
#
#
# _vendor_clients = dict()
#
#
# class ClientError(Exception):
#     pass
#
#
# class Client:
#     @staticmethod
#     def normalize_version(version: str) -> str:
#         if version == "1.8":
#             return "8"
#         return version
#
#     def __init__(self, base_url) -> None:
#         self._base_url = base_url
#
#     def get_download_url(
#         self,
#         version: str,
#         operating_system: OperatingSystem,
#         arch: Architecture,
#         impl: JvmImpl = Implementation.HOTSPOT,
#         jre: bool = False,
#     ) -> str:
#         raise NotImplementedError("get_download_url")
#
#     def download(self, download_url: str) -> Optional[str]:
#         if download_url.lower().startswith("http"):
#             req = request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
#         else:
#             raise ClientError("Invalid Download URL")
#
#         jdk_file = None
#         with request.urlopen(req) as open_request:  # noqa: S310
#             headers = open_request.headers
#             content_disposition = headers.get_content_disposition()
#             if content_disposition:
#                 jdk_file = headers.get_filename()
#             else:
#                 url_path = urlsplit(download_url).path
#                 jdk_file = path.basename(url_path)
#
#             if jdk_file:
#                 jdk_file = path.join(tempfile.gettempdir(), jdk_file)
#                 with open(jdk_file, "wb") as out_file:
#                     shutil.copyfileobj(open_request, out_file)
#         return jdk_file
#
#
# def download_resumable(download_url: str) -> Optional[str]:
#     """
#     Downloads a file from a URL with the ability to resume an interrupted download.
#     -- Google AI
#     """
#     if not download_url.lower().startswith("http"):
#         raise ClientError("Invalid Download URL")
#
#     # 1. Determine the local file path
#     url_path = urlsplit(download_url).path
#     filename = path.basename(url_path)
#     if not filename:
#         raise ClientError("Could not determine filename from URL")
#
#     jdk_file = path.join(tempfile.gettempdir(), filename)
#
#     headers = {"User-Agent": "Mozilla/5.0"}
#     resume_position = 0
#
#     # 2. Check for an existing partial file to resume from
#     if path.exists(jdk_file):
#         import os
#         resume_position = os.stat(jdk_file).st_size
#         # Add the Range header to the request to resume the download
#         headers['Range'] = f'bytes={resume_position}-'
#         print(f"Resuming download from byte {resume_position}...")
#
#     # 3. Make the HTTP request
#     response = requests.get(download_url, headers=headers, stream=True)
#     response.raise_for_status()  # Raise an exception for bad status codes
#
#     # 4. Open the destination file in append-binary mode
#     with open(jdk_file, "ab") as out_file:
#         # 5. Copy the file contents from the response to the file
#         shutil.copyfileobj(response.raw, out_file)
#
#     print(f"Download complete: {jdk_file}")
#     return jdk_file
#
# def vendor_client(
#     vendor: Union[Vendor, str, List[Vendor], List[str]]
# ) -> Callable[[Client], Client]:
#     def wrapper(client: Client) -> Client:
#         if isinstance(vendor, Iterable):
#             unique_vendors = vendor
#             for unique_vendor in unique_vendors:
#                 vendor_name = str(unique_vendor).lower()
#                 if vendor_name not in _vendor_clients:
#                     _vendor_clients[vendor_name] = client
#         else:
#             _vendor_clients[str(vendor).lower()] = client
#         return client
#
#     return wrapper
#
#
# def load_client(vendor: Optional[Union[Vendor, str]] = "Adoptium") -> Optional[Client]:
#     if vendor is None or str(vendor) == "":
#         vendor = "Adoptium"
#
#     vendor_name = str(vendor).lower()
#     if vendor_name in _vendor_clients:
#         return _vendor_clients[vendor_name]
