import os
import sys
from urllib.parse import urlparse

from src.shared.database.models.vector_database import VectorDatabase

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))


from src.shared.database.models.domain.source_control_provider_model import (
    SourceControlProviderModel,
    SupportedSourceControlProviderModel,
)
from src.shared.database.schema.tables import (
    SourceControlProvider,
    SupportedSourceControlProvider,
)


class SourceControl(VectorDatabase):
    def add_supported_source_control_provider(self, name):
        with self.session_context(self.Session()) as session:
            session.add(SupportedSourceControlProvider(name=name))
            session.commit()

    def get_supported_source_control_providers(self):
        with self.session_context(self.Session()) as session:
            providers = session.query(SupportedSourceControlProvider).all()
            return [
                SupportedSourceControlProviderModel.from_database_model(provider)
                for provider in providers
            ]

    def get_supported_source_control_provider_by_id(self, id):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SupportedSourceControlProvider)
                .filter(SupportedSourceControlProvider.id == id)
                .one_or_none()
            )
            return (
                SupportedSourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_supported_source_control_provider_by_name(self, name):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SupportedSourceControlProvider)
                .filter(SupportedSourceControlProvider.name == name)
                .one_or_none()
            )
            return (
                SupportedSourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def add_source_control_provider(
        self,
        user_id,
        supported_source_control_provider: SupportedSourceControlProviderModel,
        name,
        url,
        requires_auth,
        access_token,
    ):

        if self.get_source_control_provider_by_name(user_id=user_id, name=name):
            raise Exception(
                f"A source control provider with the name {name} already exists."
            )

        if self.get_source_control_provider_from_url(user_id=user_id, url=url):
            raise Exception(
                f"A source control provider with the same domain '{self._get_domain_name(url)}' already exists."
            )

        with self.session_context(self.Session()) as session:
            session.add(
                SourceControlProvider(
                    user_id=user_id,
                    supported_source_control_provider_id=supported_source_control_provider.id,
                    source_control_provider_name=name,
                    source_control_provider_url=url,
                    requires_authentication=requires_auth,
                    source_control_access_token=access_token or None,
                )
            )
            session.commit()

    def update_source_control_provider(
        self,
        id,
        supported_source_control_provider: SupportedSourceControlProviderModel,
        name,
        url,
        requires_auth,
        access_token,
    ):
        with self.session_context(self.Session()) as session:
            session.query(SourceControlProvider).filter(
                SourceControlProvider.id == id
            ).update(
                {
                    SourceControlProvider.supported_source_control_provider_id: supported_source_control_provider.id,
                    SourceControlProvider.source_control_provider_name: name,
                    SourceControlProvider.source_control_provider_url: url,
                    SourceControlProvider.requires_authentication: requires_auth,
                    SourceControlProvider.source_control_access_token: access_token,
                }
            )
            session.commit()

    def delete_source_control_provider_by_id(self, id):
        with self.session_context(self.Session()) as session:
            session.query(SourceControlProvider).filter(
                SourceControlProvider.id == id
            ).delete()
            session.commit()

    def get_all_source_control_providers_for_user(self, user_id):
        with self.session_context(self.Session()) as session:
            providers = (
                session.query(SourceControlProvider)
                .filter(SourceControlProvider.user_id == user_id)
                .all()
            )
            return [
                SourceControlProviderModel.from_database_model(provider)
                for provider in providers
            ]

    def get_source_control_provider_by_id(self, id):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SourceControlProvider)
                .filter(SourceControlProvider.id == id)
                .one_or_none()
            )
            return (
                SourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_source_control_provider_by_name(self, user_id, name):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SourceControlProvider)
                .filter(
                    SourceControlProvider.user_id == user_id,
                    SourceControlProvider.source_control_provider_name == name,
                )
                .one_or_none()
            )
            return (
                SourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_source_control_provider_from_url(self, user_id, url: str):
        """
        Returns the source control provider from a URL.

        :param url: The URL to parse.
        :return: The source control provider.
        """
        # Find the source control provider that starts with the URL (case insensitive)
        providers = self.get_all_source_control_providers_for_user(user_id=user_id)

        domain = self._get_domain_name(url)

        for provider in providers:
            if (
                domain.lower()
                == self._get_domain_name(provider.source_control_provider_url).lower()
            ):
                return SourceControlProviderModel.from_database_model(provider)

        return None

    def _get_domain_name(self, url):
        try:
            # Parse the URL and extract the netloc part which contains the domain name
            parsed_url = urlparse(url)
            # Split the netloc by '.' and take the last two parts as domain
            # This works for most common URLs
            domain_parts = parsed_url.netloc.split(".")
            domain = ".".join(domain_parts[-2:])
            return domain
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
