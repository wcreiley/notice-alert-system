import pathway as pw
from pprint import pprint
from pathway.stdlib.indexing.nearest_neighbors import BruteForceKnnFactory
from pathway.xpacks.llm import llms
from pathway.xpacks.llm.document_store import DocumentStore
from pathway.xpacks.llm.embedders import OpenAIEmbedder
from pathway.xpacks.llm.parsers import ParseUnstructured

from pathway.xpacks.llm.splitters import TokenCountSplitter

from dotenv import load_dotenv
import os

load_dotenv()

documents = pw.io.fs.read("./data/", format="binary", with_metadata=True)

text_splitter = TokenCountSplitter(
    min_tokens=100, max_tokens=500, encoding_name="cl100k_base"
)
# embedder = OpenAIEmbedder(api_key=os.environ["OPENAI_API_KEY"], model="text-embedding-ada-002")
embedder = OpenAIEmbedder(api_key=os.environ["OPENAI_API_KEY"])

retriever_factory = BruteForceKnnFactory(
    embedder=embedder,
)

parser = ParseUnstructured(
    chunking_mode="by_title",
    chunking_kwargs={
        "max_characters": 3000,
        "new_after_n_chars": 2000,
    },
)

document_store = DocumentStore(
    docs=documents,
    retriever_factory=retriever_factory,
    parser=parser,
    splitter=text_splitter,
)

webserver = pw.io.http.PathwayWebserver(host="0.0.0.0", port=8011)


class QuerySchema(pw.Schema):
    messages: str


queries, writer = pw.io.http.rest_connector(
    webserver=webserver,
    schema=QuerySchema,
    autocommit_duration_ms=50,
    delete_completed_queries=False,
)

queries = queries.select(
    query=pw.this.messages,
    k=1,
    metadata_filter=None,
    filepath_globpattern=None,
)

retrieved_documents = document_store.retrieve_query(queries)
retrieved_documents = retrieved_documents.select(docs=pw.this.result)
queries_context = queries + retrieved_documents


def get_context(documents):
    content_list = []
    for doc in documents:
        content_list.append(str(doc["text"]))
    return " ".join(content_list)


@pw.udf
def build_prompts_udf(documents, query) -> str:
    context = get_context(documents)
    prompt = (
        f"Given the following documents : \n {context} \nanswer this query: {query}"
    )
    # pprint("Prompt: ", prompt)
    return prompt
    # return "What is the definition of humble?"


prompts = queries_context + queries_context.select(
    result=build_prompts_udf(pw.this.docs, pw.this.query)
)
# print("Prompts: ")
# pprint(prompts)

# prompts: pw.Table = pw.debug.table_from_markdown('''humble''')

model = llms.OpenAIChat(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],  # Read OpenAI API key from environmental variables
)

# listOfThings = pw.this.without(pw.this.query, pw.this.prompts, pw.this.docs)
# print("WES: ")
# pprint(*listOfThings)
# for item in listOfThings:
#     print("Item: ")
#     pprint(item)
#     for item2 in item:
#         print("Item2: ")
#         pprint(item2)

response = prompts.select(*pw.this.without(pw.this.query, pw.this.docs))
# response = prompts.select(
#     *pw.this.without(pw.this.query, pw.this.docs),
#     result=model("something")
# )
# response = prompts.select(
#     *pw.this.without(pw.this.query, pw.this.prompts, pw.this.docs),
#     result=model(
#         llms.prompt_chat_single_qa(pw.this.prompts),
#     ),
# )

writer(response)

pw.run()
