from storages.backends.s3boto3 import S3Boto3Storage

class StaticRootS3Boto3Storage(S3Boto3Storage):
    location = "static"
    default_acl = None
    file_overwrite = True

class MediaRootS3Boto3Storage(S3Boto3Storage):
    location = "media"
    default_acl = None
    file_overwrite = False  # we use UUIDs anyway

    # ⬇️ This avoids HeadObject (the cause of your 403)
    def exists(self, name):
        """
        Always returns False to prevent Django from checking if a file exists in S3 before saving.
        This avoids unnecessary HeadObject requests, which can cause 403 errors with certain S3 permissions.
        As a result, files will always be overwritten if the same name is used, but since UUIDs are used for filenames,
        the risk of collision is minimal.
        """
        return False
