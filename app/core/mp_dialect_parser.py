import os
import re
import json
import logging
from typing import Dict, Any, Tuple
import frontmatter
from datetime import datetime
from core.models import LessonMetadata, SlideDirective

logger = logging.getLogger(__name__)

class MPDialectParser:
    """
    Compiler for the Content-OS MP-Dialect.
    Extracts YAML metadata, parses !slide{} DSL directives, counts ellipsis pauses,
    and returns a structured Pydantic model (which becomes the .json sovereign).
    """

    # Regex to find: !slide{ "layout": "Title", "content": "..." }
    # Matches '!slide' followed by anything inside braces {}
    SLIDE_REGEX = re.compile(r'!slide\s*(\{(?:[^{}]+|(?:\{[^{}]*\})|(?:\{[^{}]*\{[^{}]*\}[^{}]*\}))*\})')
    
    # Regex to find rhythmic pauses (exact '...')
    ELLIPSIS_REGEX = re.compile(r'\.\.\.')

    def __init__(self):
        # Allow Words-Per-Minute to be configurable via environment
        try:
            self.wpm = int(os.getenv("CONTENT_OS_WORDS_PER_MINUTE", "150"))
        except ValueError:
            self.wpm = 150
            logger.warning("Invalid CONTENT_OS_WORDS_PER_MINUTE. Falling back to 150.")

    def parse_markdown_file(self, md_path: str) -> LessonMetadata:
        """
        Reads a .md file and computes the LessonMetadata object.
        """
        if not os.path.exists(md_path):
            raise FileNotFoundError(f"Source Markdown file not found: {md_path}")

        logger.info(f"Compiling Markdown file: {md_path}")
        with open(md_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        title = post.metadata.get('title', 'Untitled Lesson')
        module = post.metadata.get('module', 'Uncategorized')
        
        body_content = post.content

        # 1. Extract Slides
        slides, cleaned_body = self._extract_slides(body_content)

        # 2. Extract Ellipses (...)
        ellipsis_count = len(self.ELLIPSIS_REGEX.findall(cleaned_body))

        # 3. Word Count (Clean text without slide directives)
        # Remove punctuation for more accurate word counting if desired, 
        # but a simple split is usually sufficient for script timing.
        words = cleaned_body.split()
        word_count = len([w for w in words if w.strip()])

        # 4. Time Calculation
        # T_total = (WordCount / WPM * 60) + (EllipsisCount * 2)
        duration_from_words = (word_count / self.wpm) * 60.0
        duration_from_pauses = ellipsis_count * 2.0
        total_seconds = int(round(duration_from_words + duration_from_pauses))

        # 5. Hydrate Model
        metadata = LessonMetadata(
            title=title,
            module=module,
            word_count=word_count,
            ellipsis_count=ellipsis_count,
            estimated_duration_seconds=total_seconds,
            slides=slides,
            compiled_at=datetime.utcnow()
        )

        return metadata

    def _extract_slides(self, text: str) -> Tuple[list[SlideDirective], str]:
        """
        Extracts slide directives and returns (List of Slides, Text Without Slides).
        """
        slides = []
        
        # Find all JSON blocks inside !slide{}
        matches = self.SLIDE_REGEX.finditer(text)
        
        for match in matches:
            raw_json_str = match.group(1)
            try:
                # Need to safely parse the JSON. Since it's authored by humans, 
                # we must be prepared for minor syntax errors.
                parsed_json = json.loads(raw_json_str)
                layout = parsed_json.get("layout", "Default")
                content = parsed_json.get("content", "")
                
                # We enforce single space before/after '=' for assignments per Physician-Programmer standards,
                # so here we explicitly map to the pydantic model cleanly:
                slide_obj = SlideDirective(
                    layout=layout, 
                    content=content,
                    raw_json=raw_json_str
                )
                slides.append(slide_obj)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse slide JSON block: {raw_json_str}. Error: {e}")
                
        # Remove the slide directives from the text to get the true "spoken" word count
        cleaned_text = self.SLIDE_REGEX.sub('', text)
        
        return slides, cleaned_text

# Singleton parser
compiler = MPDialectParser()
