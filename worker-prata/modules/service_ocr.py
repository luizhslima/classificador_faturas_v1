from docling.datamodel.base_models import InputFormat, DocumentStream
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.datamodel.backend_options import PdfBackendOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from pydantic import SecretStr
from abc import ABC, abstractmethod
from modules.extrator_nubank import processar_fatura_nativo

import io

from typedict.fatura import FaturaDict

class ServiceOCR(ABC):
    @abstractmethod
    def processar_pdf_nativo(self, bytes: io.BytesIO) -> FaturaDict:
        "Metodo responsavel por processar o recurso do OCR"
        pass


class ServiceRapidOCR(ServiceOCR):
    def __init__(self) -> None:
        opcoes_acelerador = AcceleratorOptions(
            device="cuda"
        )

        opcoes_backend = PdfBackendOptions(
            enable_remote_fetch=False,
            enable_local_fetch=False,    # Bloqueia busca de arquivos locais
            kind='pdf',                  # Identificador do tipo de backend
            password=SecretStr("405152"),# Senha protegida na memória
            enforce_same_font=False
        )

        opcoes_pipeline = PdfPipelineOptions(
            accelerator_options=opcoes_acelerador
        )

        opcoes_pipeline.do_ocr = False

        opcoes_pipeline.ocr_options = RapidOcrOptions(
            force_full_page_ocr=False
        )

        self.conversor = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.IMAGE],
            format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=opcoes_pipeline,
                        backend=PyPdfiumDocumentBackend, # <--- A MÁGICA ACONTECE AQUI
                        backend_options=opcoes_backend),
                    }
        )
    def processar_pdf_nativo(self, bytes: io.BytesIO) -> FaturaDict:
        return processar_fatura_nativo(self.conversor,bytes)