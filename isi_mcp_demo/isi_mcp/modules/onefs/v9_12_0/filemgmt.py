import os
from pathlib import PurePosixPath

import isilon_sdk.v9_12_0 as isi_sdk
from isilon_sdk.v9_12_0.models.namespace_acl import NamespaceAcl
from isilon_sdk.v9_12_0.models.acl_object import AclObject
from isilon_sdk.v9_12_0.models.member_object import MemberObject
from isilon_sdk.v9_12_0.models.namespace_metadata import NamespaceMetadata
from isilon_sdk.v9_12_0.models.namespace_metadata_attrs import NamespaceMetadataAttrs
from isilon_sdk.v9_12_0.models.directory_query import DirectoryQuery
from isilon_sdk.v9_12_0.models.directory_query_scope import DirectoryQueryScope
from isilon_sdk.v9_12_0.models.directory_query_scope_conditions import DirectoryQueryScopeConditions
from isilon_sdk.v9_12_0.models.access_point_create_params import AccessPointCreateParams
from isilon_sdk.v9_12_0.models.worm_create_params import WormCreateParams

MAX_FILE_CONTENT_SIZE = 1 * 1024 * 1024  # 1 MiB


class FileMgmt:
    """Namespace and file management operations on a PowerScale cluster."""

    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = cluster.debug

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _ns_api(self):
        """Create and return a NamespaceApi instance."""
        return isi_sdk.NamespaceApi(self.cluster.api_client)

    def _normalize_path(self, path: str, strip: bool = True) -> str:
        """
        Normalize and validate a path for Namespace API operations.

        Converts both absolute paths (/ifs/data/projects) and relative paths
        (ifs/data/projects, data/projects) to relative format without leading slash.

        Security: rejects path-traversal sequences (any ``..`` component) so a
        caller cannot escape the intended directory boundary. Optionally enforces
        an allowed root prefix when the FILEMGMT_ROOT_PREFIX environment variable
        is set (e.g. ``ifs`` or ``/ifs``). Root enforcement is OFF by default
        because access-point-relative paths are not rooted at /ifs.

        Args:
            path: Path string (absolute or relative)
            strip: When True (the default) the returned value has leading/trailing
                slashes removed — the relative form the Namespace URL path expects.
                When False the original string is returned unchanged on success;
                only the ``..`` traversal check (and root-prefix check) runs. Use
                strip=False for values whose required wire format is not the bare
                relative path (e.g. move/copy source/destination set via header,
                and the absolute target of an access point).

        Returns:
            Normalized path (slash-stripped when ``strip`` is True, otherwise the
            original string).

        Raises:
            ValueError: if the path contains a ``..`` traversal component or
                (when configured) falls outside the allowed root prefix.
        """
        if not path:
            return path
        # Compute the slash-stripped value for validation regardless of strip mode
        # so 'a/../b', '../etc', '/ifs/..' are all checked consistently.
        stripped = path.lstrip('/').rstrip('/')

        # Reject path traversal: no component may be '..'. This is checked on the
        # normalized (slash-stripped) value so 'a/../b', '../etc', and 'a/..'
        # are all rejected regardless of leading slashes.
        parts = PurePosixPath(stripped).parts
        if any(part == '..' for part in parts):
            raise ValueError(
                f"Invalid path '{path}': '..' path traversal is not allowed."
            )

        # Optional root-prefix enforcement (opt-in via env var). Disabled by
        # default so access-point-relative paths continue to work.
        root_prefix = os.environ.get("FILEMGMT_ROOT_PREFIX", "").strip().strip('/')
        if root_prefix:
            allowed = PurePosixPath(root_prefix).parts
            if parts[:len(allowed)] != allowed:
                raise ValueError(
                    f"Invalid path '{path}': must be within '/{root_prefix}'."
                )

        return stripped if strip else path

    def _ran_path(self, path: str) -> str:
        """
        Build a full RESTful Access to Namespace (RAN) path for header values.

        OneFS move/copy operations carry the destination (``x-isi-ifs-set-location``)
        and copy source (``x-isi-ifs-copy-source``) as HTTP headers whose values must
        be full RAN paths prefixed with ``/namespace`` (e.g. ``/namespace/ifs/dir/file``).
        Passing a bare ``/ifs/...`` value causes the cluster to return 400 Bad Request.

        Runs the same ``..`` traversal / root-prefix validation as ``_normalize_path``,
        then returns ``/namespace/<relative path>``.
        """
        return "/namespace/" + self._normalize_path(path)

    def _parse_headers(self, headers):
        """Convert HTTPHeaderDict to a plain dict."""
        return dict(headers) if headers else {}

    # -------------------------------------------------------------------
    # Directory operations
    # -------------------------------------------------------------------

    def list_directory(self, path: str, detail: str = 'default',
                       limit: int = 1000, resume: str = None,
                       sort: str = None, dir: str = None,
                       type: str = None, hidden: bool = False,
                       access_point: str = None) -> dict:
        api = self._ns_api()
        # Normalize path: strip slashes and reject '..' traversal
        path = self._normalize_path(path)
        kwargs = {'detail': detail, 'limit': limit}
        if resume:
            kwargs['resume'] = resume
        if sort:
            kwargs['sort'] = sort
        if dir:
            kwargs['dir'] = dir
        if type:
            kwargs['type'] = type
        if hidden:
            kwargs['hidden'] = hidden

        if access_point:
            result = api.get_directory_with_access_point_container_path(
                access_point, path, **kwargs)
        else:
            result = api.get_directory_contents(path, **kwargs)

        children = [c.to_dict() for c in result.children] if result.children else []
        return {
            "children": children,
            "resume": result.resume,
            "has_more": bool(result.resume)
        }

    def create_directory(self, path: str, recursive: bool = True,
                         access_control: str = None,
                         overwrite: bool = False,
                         access_point: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {}
        if access_control:
            kwargs['x_isi_ifs_access_control'] = access_control
        if recursive is not None:
            kwargs['recursive'] = recursive
        if overwrite:
            kwargs['overwrite'] = overwrite

        if access_point:
            api.create_directory_with_access_point_container_path(
                access_point, path, 'container', **kwargs)
        else:
            api.create_directory(path, 'container', **kwargs)

        return {"success": True, "message": f"Directory created: {path}"}

    def delete_directory(self, path: str, recursive: bool = False,
                         access_point: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {}
        if recursive:
            kwargs['recursive'] = recursive

        if access_point:
            api.delete_directory_with_access_point_container_path(
                access_point, path, **kwargs)
        else:
            api.delete_directory(path, **kwargs)

        return {"success": True, "message": f"Directory deleted: {path}"}

    def move_directory(self, path: str, destination: str,
                       access_point: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        # destination is sent via the x-isi-ifs-set-location header and must be a
        # full RAN path (/namespace/...); reject traversal then add the prefix.
        destination = self._ran_path(destination)
        if access_point:
            api.move_directory_with_access_point_container_path(
                access_point, path, destination)
        else:
            api.move_directory(path, destination)

        return {"success": True, "message": f"Directory moved from {path} to {destination}"}

    def get_directory_attributes(self, path: str) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        data, status, headers = api.get_directory_attributes_with_http_info(path)
        return self._parse_headers(headers)

    # -------------------------------------------------------------------
    # File operations
    # -------------------------------------------------------------------

    def get_file_contents(self, path: str, byte_range: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {'_preload_content': False}
        if byte_range:
            kwargs['range'] = byte_range

        data, status, headers = api.get_file_contents_with_http_info(path, **kwargs)

        raw_bytes = data.data
        size = len(raw_bytes)
        truncated = size > MAX_FILE_CONTENT_SIZE

        if truncated:
            raw_bytes = raw_bytes[:MAX_FILE_CONTENT_SIZE]

        try:
            text = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            text = raw_bytes.decode('latin-1')

        return {
            "contents": text,
            "size": size,
            "truncated": truncated,
            "headers": self._parse_headers(headers)
        }

    def create_file(self, path: str, contents: str = '',
                    access_control: str = None,
                    content_type: str = None,
                    overwrite: bool = False) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {}
        if access_control:
            kwargs['x_isi_ifs_access_control'] = access_control
        if content_type:
            kwargs['content_type'] = content_type
        if overwrite:
            kwargs['overwrite'] = overwrite

        api.create_file(path, 'object', contents, **kwargs)
        return {"success": True, "message": f"File created: {path}"}

    def delete_file(self, path: str) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        api.delete_file(path)
        return {"success": True, "message": f"File deleted: {path}"}

    def move_file(self, path: str, destination: str) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        # destination is sent via the x-isi-ifs-set-location header and must be a
        # full RAN path (/namespace/...); reject traversal then add the prefix.
        destination = self._ran_path(destination)
        api.move_file(path, destination)
        return {"success": True, "message": f"File moved from {path} to {destination}"}

    def get_file_attributes(self, path: str) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        data, status, headers = api.get_file_attributes_with_http_info(path)
        return self._parse_headers(headers)

    # -------------------------------------------------------------------
    # Copy operations
    # -------------------------------------------------------------------

    def copy_directory(self, source: str, destination: str,
                       overwrite: bool = False, merge: bool = False,
                       continue_on_error: bool = False) -> dict:
        api = self._ns_api()
        # destination is the URL path (relative form); source is sent via the
        # x-isi-ifs-copy-source header and must be a full RAN path (/namespace/...).
        destination = self._normalize_path(destination)
        source = self._ran_path(source)
        kwargs = {}
        if overwrite:
            kwargs['overwrite'] = overwrite
        if merge:
            kwargs['merge'] = merge
        if continue_on_error:
            kwargs['_continue'] = continue_on_error

        result = api.copy_directory(destination, source, **kwargs)

        errors = []
        if result and hasattr(result, 'copy_errors') and result.copy_errors:
            errors = [e.to_dict() for e in result.copy_errors]

        return {
            "success": len(errors) == 0,
            "errors": errors,
            "message": f"Directory copied from {source} to {destination}"
        }

    def copy_file(self, source: str, destination: str,
                  overwrite: bool = False, clone: bool = False,
                  snapshot: str = None) -> dict:
        api = self._ns_api()
        # destination is the URL path (relative form); source is sent via the
        # x-isi-ifs-copy-source header and must be a full RAN path (/namespace/...).
        destination = self._normalize_path(destination)
        source = self._ran_path(source)
        kwargs = {}
        if overwrite:
            kwargs['overwrite'] = overwrite
        if clone:
            kwargs['clone'] = clone
        if snapshot:
            kwargs['snapshot'] = snapshot

        result = api.copy_file(destination, source, **kwargs)

        errors = []
        if result and hasattr(result, 'copy_errors') and result.copy_errors:
            errors = [e.to_dict() for e in result.copy_errors]

        return {
            "success": len(errors) == 0,
            "errors": errors,
            "message": f"File copied from {source} to {destination}"
        }

    # -------------------------------------------------------------------
    # ACL operations
    # -------------------------------------------------------------------

    def get_acl(self, path: str, nsaccess: bool = None,
                zone: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {}
        if nsaccess is not None:
            kwargs['nsaccess'] = nsaccess
        if zone:
            kwargs['zone'] = zone

        result = api.get_acl(path, True, **kwargs)
        return result.to_dict()

    def set_acl(self, path: str, mode: str = None,
                owner: str = None, group: str = None,
                acl: list = None, action: str = 'replace',
                authoritative: str = None,
                nsaccess: bool = None, zone: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)

        acl_objects = None
        if acl:
            acl_objects = []
            for entry in acl:
                trustee = None
                if 'trustee' in entry:
                    t = entry['trustee']
                    trustee = MemberObject(
                        id=t.get('id'), name=t.get('name'), type=t.get('type'))
                acl_objects.append(AclObject(
                    accessrights=entry.get('accessrights'),
                    accesstype=entry.get('accesstype'),
                    inherit_flags=entry.get('inherit_flags'),
                    op=entry.get('op'),
                    trustee=trustee
                ))

        owner_obj = None
        if owner:
            owner_obj = MemberObject(name=owner, type='user')

        group_obj = None
        if group:
            group_obj = MemberObject(name=group, type='group')

        namespace_acl = NamespaceAcl(
            acl=acl_objects,
            action=action,
            authoritative=authoritative,
            group=group_obj,
            mode=mode,
            owner=owner_obj
        )

        kwargs = {}
        if nsaccess is not None:
            kwargs['nsaccess'] = nsaccess
        if zone:
            kwargs['zone'] = zone

        api.set_acl(path, True, namespace_acl, **kwargs)
        return {"success": True, "message": f"ACL set on {path}"}

    # -------------------------------------------------------------------
    # Metadata operations
    # -------------------------------------------------------------------

    def get_metadata(self, path: str, is_directory: bool = True,
                     zone: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        kwargs = {}
        if zone:
            kwargs['zone'] = zone

        if is_directory:
            result = api.get_directory_metadata(path, True, **kwargs)
        else:
            result = api.get_file_metadata(path, True, **kwargs)

        attrs = [a.to_dict() for a in result.attrs] if result.attrs else []
        return {"attrs": attrs}

    def set_metadata(self, path: str, attrs: list,
                     action: str = 'update',
                     is_directory: bool = True,
                     zone: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)

        attr_objects = []
        for a in attrs:
            attr_objects.append(NamespaceMetadataAttrs(
                name=a.get('name'),
                namespace=a.get('namespace'),
                op=a.get('op'),
                value=a.get('value')
            ))

        metadata = NamespaceMetadata(action=action, attrs=attr_objects)

        kwargs = {}
        if zone:
            kwargs['zone'] = zone

        if is_directory:
            api.set_directory_metadata(path, True, metadata, **kwargs)
        else:
            api.set_file_metadata(path, True, metadata, **kwargs)

        return {"success": True, "message": f"Metadata set on {path}"}

    # -------------------------------------------------------------------
    # Access point operations
    # -------------------------------------------------------------------

    def list_access_points(self, versions: bool = False) -> dict:
        api = self._ns_api()
        kwargs = {}
        if versions:
            kwargs['versions'] = versions

        result = api.list_access_points(**kwargs)
        return result.to_dict()

    def create_access_point(self, name: str, path: str) -> dict:
        api = self._ns_api()
        # path is the absolute namespace target stored in cluster config; preserve
        # its form (do not strip leading slash) but still reject '..' traversal.
        path = self._normalize_path(path, strip=False)
        params = AccessPointCreateParams(path=path)
        api.create_access_point(name, params)
        return {"success": True, "message": f"Access point '{name}' created at {path}"}

    def delete_access_point(self, name: str) -> dict:
        api = self._ns_api()
        api.delete_access_point(name)
        return {"success": True, "message": f"Access point '{name}' deleted"}

    # -------------------------------------------------------------------
    # WORM / SmartLock operations
    # -------------------------------------------------------------------

    def get_worm_properties(self, path: str) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        result = api.get_worm_properties(path, True)
        return result.to_dict()

    def set_worm_properties(self, path: str,
                            commit_to_worm: bool = False,
                            worm_retention_date: str = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)
        params = WormCreateParams(
            commit_to_worm=commit_to_worm,
            worm_retention_date=worm_retention_date
        )
        api.set_worm_properties(path, True, params)
        return {"success": True, "message": f"WORM properties set on {path}"}

    # -------------------------------------------------------------------
    # Directory query
    # -------------------------------------------------------------------

    def query_directory(self, path: str, conditions: list,
                        logic: str = 'and', result_attrs: list = None,
                        limit: int = 1000, resume: str = None,
                        detail: str = None, sort: str = None,
                        dir: str = None, type: str = None,
                        hidden: bool = False,
                        max_depth: int = None) -> dict:
        api = self._ns_api()
        path = self._normalize_path(path)

        cond_objects = []
        for c in conditions:
            value = c.get('value', '')
            if c.get('operator') == 'like' and isinstance(value, str):
                # PAPI uses SQL LIKE wildcards (% = any chars, _ = one char), not shell globs.
                # Translate shell-style * and ? so callers can use either syntax.
                value = value.replace('*', '%').replace('?', '_')
            cond_objects.append(DirectoryQueryScopeConditions(
                attr=c.get('attr'),
                operator=c.get('operator'),
                value=value
            ))

        scope = DirectoryQueryScope(conditions=cond_objects, logic=logic)
        query_model = DirectoryQuery(result=result_attrs, scope=scope)

        kwargs = {'limit': limit}
        if resume:
            kwargs['resume'] = resume
        if detail:
            kwargs['detail'] = detail
        if sort:
            kwargs['sort'] = sort
        if dir:
            kwargs['dir'] = dir
        if type:
            kwargs['type'] = type
        if hidden:
            kwargs['hidden'] = hidden
        if max_depth is not None:
            kwargs['max_depth'] = max_depth

        result = api.query_directory(path, True, query_model, **kwargs)

        children = [c.to_dict() for c in result.children] if result.children else []
        has_like = any(c.get('operator') == 'like' for c in conditions)
        out = {
            "children": children,
            "resume": result.resume,
            "has_more": bool(result.resume)
        }
        if not children and not result.resume and has_like:
            out["_warning"] = (
                "No results returned for 'like' operator. The PowerScale namespace query "
                "API may not support wildcard pattern matching on the 'name' attribute on "
                "this OneFS version. Confirmed working alternative: use operator='=' for "
                "exact filename matches."
            )
        return out
