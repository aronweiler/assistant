import re
import logging
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
from langchain.docstore.document import Document
from bs4 import BeautifulSoup


class PDFLoader:
    def __init__(self, file_path):
        self.file_path = file_path

    def extract_page_number(self, html_string):
        pattern = r'<a name="(\d+)">'
        match = re.search(pattern, html_string)
        if match:
            number = int(match.group(1))
            return number
        else:
            return None

    def process_doc(self, data: Document):
        soup = BeautifulSoup(data.page_content, "html.parser")
        content = soup.find_all("div")

        cur_page = 1
        cur_fs = None
        cur_text = ""
        snippets = []  # first collect all snippets that have the same font size
        for c in content:
            if len(c) > 0:
                temp_page = self.extract_page_number(str(c.contents[0]))

                if temp_page != None:
                    if cur_page != temp_page:
                        # did we have any text that is spanning a page break?
                        # treat it like a font size change, and complete the snippet
                        snippets.append((cur_text, cur_fs, cur_page))
                        cur_text = c.text
                        cur_page = temp_page
                        continue

            logging.debug("Page: ", cur_page)
            sp = c.find("span")
            if not sp:
                continue
            st = sp.get("style")
            if not st:
                continue
            fs = re.findall("font-size:(\d+)px", st)
            if not fs:
                continue
            fs = int(fs[0])
            if not cur_fs:
                cur_fs = fs
            if fs == cur_fs:
                cur_text += c.text
            else:
                snippets.append((cur_text, cur_fs, cur_page))
                cur_fs = fs
                cur_text = c.text
        snippets.append((cur_text, cur_fs, cur_page))
        # Note: The above logic is very straightforward. One can also add more strategies such as removing duplicate snippets (as
        # headers/footers in a PDF appear on multiple pages so if we find duplicatess safe to assume that it is redundant info)

        cur_idx = -1
        semantic_snippets = []
        # Assumption: headings have higher font size than their respective content
        for s in snippets:
            # if current snippet's font size > previous section's heading => it is a new heading
            # or it could be the beginning of the first page, or a header of some sort.
            heading_font = 0

            if semantic_snippets:
                heading_font = semantic_snippets[cur_idx].metadata.get(
                    "heading_font", 0
                )
                if heading_font is None:
                    heading_font = 0

            if not semantic_snippets or (s[1] is not None and s[1] > heading_font):
                # throw the 'heading', or whatever it is, into the heading metadata, but also into content
                # TODO: look at deduping the various headings (in the case of headers/footers)
                metadata = {
                    "heading": s[0],
                    "content_font": 0,
                    "heading_font": s[1],
                    "page": s[2],
                }
                metadata.update(data.metadata)
                semantic_snippets.append(Document(page_content=s[0], metadata=metadata))
                cur_idx += 1
                continue

            # if the current snippet's page is different, ignore this section
            if semantic_snippets[cur_idx].metadata["page"] == s[2]:
                # if current snippet's font size <= previous section's content => content belongs to the same section (one can also create
                # a tree like structure for sub sections if needed but that may require some more thinking and may be data specific)
                if (
                    not semantic_snippets[cur_idx].metadata["content_font"]
                    or s[1] <= semantic_snippets[cur_idx].metadata["content_font"]
                ):
                    semantic_snippets[cur_idx].page_content += s[0]
                    semantic_snippets[cur_idx].metadata["content_font"] = max(
                        s[1], semantic_snippets[cur_idx].metadata["content_font"]
                    )
                    continue

            # if current snippet's font size > previous section's content but less tha previous section's heading than also make a new
            # section (e.g. title of a pdf will have the highest font size but we don't want it to subsume all sections)
            metadata = {
                "heading": s[0],
                "content_font": 0,
                "heading_font": s[1],
                "page": s[2],
            }
            metadata.update(data.metadata)
            semantic_snippets.append(Document(page_content="", metadata=metadata))
            cur_idx += 1

        return semantic_snippets

    def load(self):
        loader = PDFMinerPDFasHTMLLoader(self.file_path)

        data = loader.load()[0]  # entire pdf is loaded as a single Document

        return self.process_doc(data)


# loader = PDFLoader("C:\\Repos\\DocTalk\\src\\runners\\cvss\\documents\\spec\\cvss-v31-specification_r1.pdf")
# docs = loader.load()
# logging.debug(docs[0].page_content)
