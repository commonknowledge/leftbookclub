import urllib.parse
from storages.backends.s3boto3 import S3Boto3Storage

class DigitalOceanSpacesStorage(S3Boto3Storage):
    def url(self, name, parameters=None, expire=None, http_method=None):
        s3_url = super().url(name, parameters, expire, http_method)

        # Behave like s3 if no custom domain
        if not self.custom_domain:
            return s3_url

        # Otherwise, take the signature from the origin url and append it to the cdn url
        params = parameters.copy() if parameters else {}
        params['Bucket'] = self.bucket.name
        params['Key'] = name
        signed_url = self.bucket.meta.client.generate_presigned_url('get_object', Params=params,
                                                                    ExpiresIn=expire, HttpMethod=http_method)

        url_parts = urllib.parse.urlparse(s3_url)
        signed_url_parts = urllib.parse.urlparse(signed_url)

        url_parts = urllib.parse.ParseResult(
            query=signed_url_parts.query, scheme=url_parts.scheme, netloc=url_parts.netloc, path=url_parts.path, params=url_parts.params, fragment=url_parts.fragment)
        return url_parts.geturl()