from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict



class _Config:
    def __init__(self):
        self._root_dir: Path = Path(__file__).parent.absolute()

    @property
    def root_dir(self) -> Path:
        return self._root_dir
    
    @root_dir.setter
    def root_dir(self, value: str | Path) -> None:
        self._root_dir = Path(value)


    @property
    def output_dir(self) -> Path:
        d = self.root_dir / "output"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def bib_dir(self) -> Path:
        d = self.output_dir / "bib"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def pdf_dir(self) -> Path:
        d = self.output_dir / "pdf"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        d = self.root_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d    



class _Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    model_name:  str = "llama3"
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )



config: _Config     = _Config()
settings: _Settings = _Settings()