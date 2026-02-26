from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field

class SlideDirective(BaseModel):
    """
    Represents a single !slide{} directive extracted from Markdown.
    """
    layout: str = Field(description="The PPTX master slide layout to use (e.g., 'Title Only', 'Bullet Points').")
    content: str = Field(description="The primary text/content for the slide.")
    raw_json: str = Field(description="The original JSON string parsed from the directive.")

class HeptatomoTensor(BaseModel):
    """
    Rank-7 Tensor (V ∈ ℝ^7) representing the dimensional weights of content.
    Each dimension ranges from 0.0 to 1.0.
    """
    logos: float = Field(default=0.0, ge=0.0, le=1.0, description="Pure reason, philosophy, mathematics.")
    techne: float = Field(default=0.0, ge=0.0, le=1.0, description="Craftsmanship, engineering, code, architecture.")
    ethos: float = Field(default=0.0, ge=0.0, le=1.0, description="Ethics, moral duty, character.")
    bios: float = Field(default=0.0, ge=0.0, le=1.0, description="The biological, the medical, life.")
    strategos: float = Field(default=0.0, ge=0.0, le=1.0, description="Strategy, business value, growth.")
    polis: float = Field(default=0.0, ge=0.0, le=1.0, description="Public health, society, politics, impact.")
    pathos: float = Field(default=0.0, ge=0.0, le=1.0, description="Empathy, emotion, psychology.")

class LessonMetadata(BaseModel):
    """
    Represents the full data model for a course lesson (MRWD).
    """
    type: str = Field(default="lesson", description="Discriminator for the content type.")
    title: str = Field(description="The title of the lesson extracted from frontmatter.")
    module: str = Field(description="The module or section this lesson belongs to.")
    word_count: int = Field(description="Total word count of the actual spoken script.")
    ellipsis_count: int = Field(description="Number of rhythmic pauses (...) detected.")
    estimated_duration_seconds: int = Field(description="Calculated duration based on words per minute + pauses.")
    dimensional_tensor: Optional[HeptatomoTensor] = Field(default=None, description="The 7D Connectome weight representation.")
    slides: List[SlideDirective] = Field(default_factory=list, description="All slide directives found in the text.")
    compiled_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of compilation.")

class SocialPostMetadata(BaseModel):
    """
    Represents the data model for a social media post (e.g., Instagram).
    """
    type: str = Field(default="social", description="Discriminator for the content type.")
    day_number: int = Field(description="The timeline day number (e.g., 1 for Day 1).")
    platform: str = Field(description="Target social media platform (e.g., 'instagram').")
    hook: str = Field(description="The primary hook or headline of the post.")
    body_word_count: int = Field(description="Word count of the post body.")
    hashtags: List[str] = Field(default_factory=list, description="Extracted hashtags.")
    compiled_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of compilation.")

class CompilationResult(BaseModel):
    """
    The result returned by the API after compiling a Markdown file.
    """
    source_path: str = Field(description="The absolute or relative path to the original .md file.")
    metadata_path: str = Field(description="The path where the .json sovereign pair was saved.")
    metadata: Union[LessonMetadata, SocialPostMetadata] = Field(description="The parsed metadata object.")
