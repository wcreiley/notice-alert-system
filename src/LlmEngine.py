import os
import pprint

import dotenv
import asyncio

import pathway as pw
from pathway.stdlib.ml.index import KNNIndex
from pathway.xpacks.llm.embedders import OpenAIEmbedder
from pathway.xpacks.llm.llms import OpenAIChat, prompt_chat_single_qa
from pathway.xpacks.llm.parsers import ParseUnstructured
from pathway.xpacks.llm.parsers import ParseUtf8
from pathway.xpacks.llm.splitters import TokenCountSplitter


class DocumentInputSchema(pw.Schema):
    doc: str


class QueryInputSchema(pw.Schema):
    query: str
    user: str


# This is based on https://github.com/pathwaycom/llm-app/tree/main/examples/pipelines/drive_alert
class LlmEngine:

    def __init__(self):

        print("Initializing LlmEngine")

        dotenv.load_dotenv()

        # Required configuration
        self.api_key: str = os.environ.get("OPENAI_API_KEY", "")
        self.slack_alert_channel_id = os.environ.get("SLACK_ALERT_CHANNEL_ID", "")
        self.slack_alert_token = os.environ.get("SLACK_ALERT_TOKEN", "")

        # Default Configuration
        self.host: str = os.environ.get("PATHWAY_REST_CONNECTOR_HOST", "0.0.0.0")
        self.port: int = int(os.environ.get("PATHWAY_REST_CONNECTOR_PORT", "8080"))
        self.embedder_locator: str = os.environ.get("EMBEDDER_LOCATOR", "text-embedding-ada-002")
        self.embedding_dimension: int = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
        self.model_locator: str = os.environ.get("MODEL_LOCATOR", "gpt-3.5-turbo")
        self.max_tokens: int = int(os.environ.get("MAX_TOKEN", "400"))
        self.temperature: float = float(os.environ.get("TEMPERATURE", "0.0"))

        self.embedder = None
        self.index = None
        self.model = None
        self.query = None
        self.response_writer = None
        self.responses = None

    # Part I: Build index
    def build_index(self):

        self.embedder = OpenAIEmbedder(
            api_key=self.api_key,
            model=self.embedder_locator,
            retry_strategy=pw.asynchronous.FixedDelayRetryStrategy(),
            cache_strategy=pw.asynchronous.DefaultCache(),
        )

        # We start building the computational graph. Each pathway variable represents a dynamically changing table.

        files = pw.io.fs.read("./data/", format="binary", with_metadata=True)

        parser = ParseUtf8()
        documents = files.select(texts=parser(pw.this.data))
        documents = documents.flatten(pw.this.texts)
        documents = documents.select(texts=pw.this.texts[0])

        splitter = TokenCountSplitter()
        documents = documents.select(
            chunks=splitter(pw.this.texts, min_tokens=40, max_tokens=120)
        )
        documents = documents.flatten(pw.this.chunks)
        documents = documents.select(chunk=pw.this.chunks[0])
        enriched_documents = documents + documents.select(data=self.embedder(pw.this.chunk))

        # The index is updated each time a file changes.
        self.index = KNNIndex(
            data_embedding=enriched_documents.data, data=enriched_documents, n_dimensions=self.embedding_dimension
        )

    # Part II: receive queries, detect intent and prepare cleaned query
    def build_queries(self):

        @pw.udf
        def build_prompt_check_for_alert_request_and_extract_query(query: str) -> str:
            prompt = f"""Evaluate the user's query and identify if there is a request for notifications on answer alterations:
                User Query: '{query}'
            
                Respond with 'Yes' if there is a request for alerts, and 'No' if not, followed by the query without the alerting request part.
            
                Examples:
                "Tell me about windows in Pathway" => "No. Tell me about windows in Pathway"
                "Tell me and alert about windows in Pathway" => "Yes. Tell me about windows in Pathway"
                """
            return prompt

        @pw.udf
        def split_answer(answer: str) -> tuple[bool, str]:
            alert_enabled = "yes" in answer[:3].lower()
            true_query = answer[3:].strip(' ."')
            return alert_enabled, true_query

        def make_query_id(user, query) -> str:
            return str(hash(query + user))

        # The rest_connector returns a table of all queries under processing
        query, response_writer = pw.io.http.rest_connector(
            host=self.host,
            port=self.port,
            schema=QueryInputSchema,
            autocommit_duration_ms=50,
            delete_completed_queries=False,
        )

        self.model = OpenAIChat(
            api_key=self.api_key,
            model=self.model_locator,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            retry_strategy=pw.asynchronous.FixedDelayRetryStrategy(),
            cache_strategy=pw.asynchronous.DefaultCache(),
        )

        # Pre-process the queries:
        # - detect alerting intent
        # - then embed the query for nearest neighbor retrieval
        query += query.select(
            prompt=build_prompt_check_for_alert_request_and_extract_query(query.query)
        )

        query += query.select(
            tupled=split_answer(
                self.model(
                    prompt_chat_single_qa(pw.this.prompt),
                    max_tokens=100,
                )
            ),
        )

        query = query.select(
            pw.this.user,
            alert_enabled=pw.this.tupled[0],
            query=pw.this.tupled[1],
        )

        query += query.select(
            data=self.embedder(pw.this.query),
            query_id=pw.apply(make_query_id, pw.this.user, pw.this.query),
        )

        self.query = query
        self.response_writer = response_writer

    # Part III: respond to queries
    def process_queries(self):

        @pw.udf
        def build_prompt(documents, query):
            docs_str = "\n".join(
                [f"Doc-({idx}) -> {doc}" for idx, doc in enumerate(documents[::-1])]
            )
            prompt_str = f"""Given a set of documents, answer user query. If answer is not in docs, say it cant be inferred.
                    Docs: {docs_str}
                    Query: '{query}'
                    Final Response:"""
            return prompt_str

        @pw.udf
        def construct_message(response, alert_flag, metainfo=None):
            if alert_flag:
                if metainfo:
                    response += "\n" + str(metainfo)
                return response + f"\n\n Notification Sent to {self.slack_alert_channel_id}"
            return response

        # The context is a dynamic table: Pathway updates it each time:
        # - a new query arrives
        # - a source document is changed significantly enough to change the set of nearest neighbors
        query_context = self.query + self.index.get_nearest_items(self.query.data, k=3).select(
            documents_list=pw.this.chunk
        ).with_universe_of(self.query)

        # then we answer the queries using retrieved documents
        prompt = query_context.select(
            pw.this.query_id,
            pw.this.query,
            pw.this.alert_enabled,
            prompt=build_prompt(pw.this.documents_list, pw.this.query),
        )

        self.responses = prompt.select(
            pw.this.query_id,
            pw.this.query,
            pw.this.alert_enabled,
            response=self.model(
                prompt_chat_single_qa(pw.this.prompt),
            ),
        )

        output = self.responses.select(
            result=construct_message(pw.this.response, pw.this.alert_enabled)
        )

        # send the answers back to the asking users
        self.response_writer(output)

    # Part IV: send alerts about responses which changed significantly.
    def send_alerts(self):

        @pw.udf
        def construct_notification_message(query: str, response: str) -> str:
            return f'New response for question "{query}":\n{response}'

        self.responses = self.responses.filter(pw.this.alert_enabled)

        # Significant alerts are sent to the user
        alerts = self.responses.select(
            message=construct_notification_message(pw.this.query, pw.this.response)
        )
        pw.io.slack.send_alerts(alerts.message, self.slack_alert_channel_id, self.slack_alert_token)

    def run(self):
        self.build_index()
        self.build_queries()
        self.process_queries()
        self.send_alerts()

        # Execute the computation graph
        pw.run(monitoring_level=pw.MonitoringLevel.NONE)


if __name__ == "__main__":
    LlmEngine().run()
