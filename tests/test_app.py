import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import app
import ingest
import rag


class RagTests(unittest.TestCase):
    def test_ingest_aes_encrypted_pdf_with_empty_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus" / "subcarpeta"
            corpus.mkdir(parents=True)
            pdf = corpus / "guia.pdf"
            writer = PdfWriter()
            page = writer.add_blank_page(width=200, height=200)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({
                    NameObject("/F1"): DictionaryObject({
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }),
                }),
            })
            content = DecodedStreamObject()
            content.set_data(b"BT /F1 12 Tf 10 100 Td (Validar una idea) Tj ET")
            page[NameObject("/Contents")] = writer._add_object(content)
            writer.encrypt("", algorithm="AES-128")
            with pdf.open("wb") as file:
                writer.write(file)
            index = root / "index.json"
            with patch.object(ingest, "CORPUS", corpus.parent), patch.object(rag, "INDEX_PATH", index), \
                    patch.object(rag, "embed", side_effect=lambda texts: [[1.0, 0.0] for _ in texts]):
                ingest.build_index()
            chunk = json.loads(index.read_text(encoding="utf-8"))["chunks"][0]
            self.assertEqual(chunk["source"], "subcarpeta/guia.pdf")
            self.assertEqual(chunk["page"], 1)
            self.assertIn("Validar una idea", chunk["text"])

    def test_ingest_recursively_keeps_relative_paths_for_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            first = corpus / "financiacion"
            second = corpus / "planes" / "negocio"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (corpus / "raiz.txt").write_text("Documento en la raíz.", encoding="utf-8")
            (first / "guia.txt").write_text("Guía de financiación.", encoding="utf-8")
            (second / "guia.TXT").write_text("Guía de negocio.", encoding="utf-8")
            index = root / "index.json"
            with patch.object(ingest, "CORPUS", corpus), patch.object(rag, "INDEX_PATH", index), \
                    patch.object(rag, "embed", side_effect=lambda texts: [[1.0, 0.0] for _ in texts]):
                ingest.build_index()
            chunks = json.loads(index.read_text(encoding="utf-8"))["chunks"]
            self.assertEqual({chunk["source"] for chunk in chunks},
                             {"raiz.txt", "financiacion/guia.txt", "planes/negocio/guia.TXT"})
            self.assertEqual({chunk["text"] for chunk in chunks},
                             {"Documento en la raíz.", "Guía de financiación.", "Guía de negocio."})

    def test_ingest_and_answer_with_cited_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            (corpus / "guia.txt").write_text("Validar una idea mediante entrevistas.", encoding="utf-8")
            index = root / "index.json"
            with patch.object(ingest, "CORPUS", corpus), patch.object(rag, "INDEX_PATH", index), \
                    patch.object(rag, "embed", side_effect=lambda texts: [[1.0, 0.0] for _ in texts]), \
                    patch.object(rag, "ollama_post", return_value={
                        "message": {"content": json.dumps({"answer": "Realiza entrevistas.", "sources": [1]})}
                    }):
                ingest.build_index()
                response = rag.answer("¿Cómo validar?", [])
            self.assertEqual(response["answer"], "Realiza entrevistas.")
            self.assertIn("seleccionadas automáticamente", response["notice"])
            self.assertEqual(response["sources"][0]["name"], "guia.txt")
            self.assertIn("entrevistas", response["sources"][0]["excerpt"])

    def test_missing_and_invalid_sources_are_reported_as_errors(self):
        chunks = [{"source": "a.txt", "page": None, "text": "Texto", "vector": [1.0, 0.0]}]
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]):
            for content in (
                "Respuesta sin JSON.",
                json.dumps({"answer": "Respuesta sin fuentes.", "sources": []}),
                json.dumps({"answer": "Respuesta", "sources": [2]}),
                json.dumps({"answer": "Respuesta [2].", "sources": [1]}),
                json.dumps({"answer": "Respuesta", "sources": [True]}),
            ):
                with self.subTest(content=content), patch.object(
                    rag, "ollama_post", return_value={"message": {"content": content}}
                ):
                    with self.assertRaises(rag.RagError):
                        rag.answer("Pregunta", [])

    def test_model_can_abstain_without_sources(self):
        chunks = [{"source": "a.txt", "page": None, "text": "Texto", "vector": [1.0, 0.0]}]
        response = json.dumps({"answer": rag.NO_ANSWER, "sources": []})
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={"message": {"content": response}}):
            self.assertEqual(rag.answer("Pregunta", []), {"answer": rag.NO_ANSWER, "sources": []})

    def test_prompt_guides_partial_answers_and_related_concept_distinctions(self):
        chunks = [{"source": "guia.pdf", "page": 10, "text": "Texto de apoyo.", "vector": [1.0, 0.0]}]
        response = json.dumps({"answer": "Respuesta.", "sources": [1]})
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={"message": {"content": response}}) as ollama_post:
            rag.answer("¿Qué es el concepto?", [])
        system_prompt = ollama_post.call_args.args[1]["messages"][0]["content"]
        self.assertIn("Una sola fuente pertinente basta", system_prompt)
        self.assertIn("Distingue el concepto preguntado de conceptos parecidos", system_prompt)
        self.assertIn("Devuelve únicamente un objeto JSON válido", system_prompt)

    def test_one_relevant_source_is_used_when_model_abstains(self):
        chunks = [{
            "source": "entrevistas.pdf",
            "page": 31,
            "text": "Se consideran entrevistas en profundidad aquellas que tienen por objeto obtener información cualitativa de clientes potenciales.",
            "vector": [1.0, 0.0],
        }]
        response = json.dumps({"answer": rag.NO_ANSWER, "sources": []})
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={"message": {"content": response}}):
            result = rag.answer("¿Qué es una entrevista de cliente?", [])
        self.assertNotEqual(result["answer"], rag.NO_ANSWER)
        self.assertIn("entrevistas en profundidad", result["answer"])
        self.assertEqual(result["sources"][0]["name"], "entrevistas.pdf")

    def test_lexical_matching_normalizes_plural_query_terms(self):
        score = rag.lexical_scores("Lean Canvas", [{"text": "El método Canvas analiza modelos de negocio."}])[0]
        self.assertGreater(score, 0)

    def test_interview_question_promotes_interview_guidance_over_generic_client_text(self):
        chunks = [
            {"source": "marketing.pdf", "page": 8,
             "text": "El cliente es el centro de las acciones de marketing y producto para una empresa.",
             "vector": [1.0, 0.0]},
            {"source": "emprendedor.pdf", "page": 31,
             "text": "Se consideran entrevistas en profundidad aquellas que tienen por objeto obtener información cualitativa mediante una entrevista personal a clientes potenciales del sector.",
             "vector": [0.99, 0.1]},
        ]
        ranked = rag.retrieve(chunks, "¿Cómo hacer entrevistas con clientes?", [1.0, 0.0])
        self.assertEqual(ranked[0]["source"], "emprendedor.pdf")

    def test_retrieval_skips_title_only_canvas_source(self):
        chunks = [
            {"source": "portada.pdf", "page": 1,
             "text": "1 Guía para la elaboración del plan de empresa: Modelo Canvas",
             "vector": [1.0, 0.0]},
            {"source": "guia.pdf", "page": 10,
             "text": "El método Canvas se basa en un lienzo en blanco que analiza los modelos de negocio en nueve bloques.",
             "vector": [0.99, 0.1]},
        ]
        ranked = rag.retrieve(chunks, "¿Qué es Lean Canvas?", [1.0, 0.0])
        self.assertEqual(ranked[0]["source"], "guia.pdf")

    def test_long_model_output_is_trimmed_at_a_complete_sentence(self):
        chunks = [{"source": "a.txt", "page": None, "text": "Texto", "vector": [1.0, 0.0]}]
        response = json.dumps({
            "answer": "Primera frase. " + "Segunda frase. " * 50 + "6.",
            "sources": [1],
        })
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={"message": {"content": response}}):
            result = rag.answer("Pregunta", [])
        self.assertEqual(result["answer"], ("Primera frase. " + "Segunda frase. " * 50).strip())

    def test_incomplete_numbered_list_keeps_only_complete_items(self):
        response = json.dumps({
            "answer": "Trámites generales: 1. Alta fiscal. 2. Seguridad social. 3. Registro mercantil",
            "sources": [1],
        })
        chunks = [{"source": "a.txt", "page": None, "text": "Texto", "vector": [1.0, 0.0]}]
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={"message": {"content": response}}):
            result = rag.answer("Pregunta", [])
        self.assertEqual(result["answer"], "Trámites generales: 1. Alta fiscal. 2. Seguridad social.")

    def test_retrieval_uses_relevant_chunk_and_history_for_followup(self):
        chunks = [
            {"source": "otro.txt", "page": None, "text": "Otro", "vector": [0.0, 1.0]},
            {"source": "guia.pdf", "page": 3, "text": "Validación", "vector": [1.0, 0.0]},
        ]
        history = [{"role": "user", "content": "¿Cómo valido mi idea?"},
                   {"role": "assistant", "content": rag.NO_ANSWER}]
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]) as embed, \
                patch.object(rag, "ollama_post", return_value={
                    "message": {"content": json.dumps({"answer": "Más entrevistas.", "sources": [1]})}
                }) as ollama_post:
            response = rag.answer("¿Y después?", history)
        self.assertIn("¿Cómo valido mi idea?", embed.call_args.args[0][0])
        self.assertIn("¿Y después?", embed.call_args.args[0][0])
        self.assertEqual(response["sources"][0]["name"], "guia.pdf")
        self.assertEqual(response["sources"][0]["page"], 3)
        chat_payload = next(call.args[1] for call in ollama_post.call_args_list if call.args[0] == "chat")
        self.assertNotIn(rag.NO_ANSWER, chat_payload["messages"][1]["content"])

    def test_company_setup_expansion_promotes_procedural_source(self):
        chunks = [
            {"source": "autoevaluacion.pdf", "page": 250,
             "text": "¿Cuánto dinero necesito para crear su empresa? ¿Tiene dinero propio o ajeno?",
             "vector": [1.0, 0.0]},
            {"source": "tramites.pdf", "page": 75,
             "text": "Para constituir una empresa hay que elegir la forma jurídica y realizar trámites fiscales y laborales.",
             "vector": [0.9, 0.1]},
        ]
        ranked = rag.retrieve(chunks, "¿Qué necesito para crear una empresa?", [1.0, 0.0])
        self.assertEqual(ranked[0]["source"], "tramites.pdf")

    def test_standalone_question_does_not_inherit_unrelated_history(self):
        chunks = [{"source": "guia.pdf", "page": 1, "text": "Pasos para crear una empresa.", "vector": [1.0, 0.0]}]
        history = [{"role": "user", "content": "¿Cómo diseño un modelo de negocio?"}]
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]) as embed, \
                patch.object(rag, "ollama_post", return_value={
                    "message": {"content": json.dumps({"answer": "Define tu idea.", "sources": [1]})}
                }) as ollama_post:
            rag.answer("¿Qué necesito para crear una empresa?", history)
        self.assertNotIn("modelo de negocio", embed.call_args.args[0][0])
        chat_payload = next(call.args[1] for call in ollama_post.call_args_list if call.args[0] == "chat")
        self.assertNotIn("modelo de negocio", chat_payload["messages"][1]["content"])
        self.assertFalse(rag.is_follow_up("¿Y una entrevista de cliente?"))
        self.assertTrue(rag.is_follow_up("¿Y después?"))

    def test_lexical_retrieval_promotes_instructions_over_a_similar_title(self):
        chunks = [
            {"source": "indice.pdf", "page": 1, "text": "Generación de modelos de negocio.",
             "vector": [1.0, 0.0]},
            {"source": "guia.pdf", "page": 14,
             "text": "Para empezar a diseñar un modelo de negocio, identifica la clientela y define la propuesta de valor.",
             "vector": [0.9, 0.1]},
        ]
        with patch.object(rag, "load_index", return_value=chunks), \
                patch.object(rag, "embed", return_value=[[1.0, 0.0]]), \
                patch.object(rag, "ollama_post", return_value={
                    "message": {"content": json.dumps({"answer": "Empieza por la clientela.", "sources": [1]})}
                }):
            response = rag.answer("¿Cómo puedo empezar a diseñar un modelo de negocio?", [])
        self.assertEqual(response["sources"][0]["name"], "guia.pdf")

    def test_failed_ingestion_preserves_previous_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            (corpus / "vacio.txt").write_text("", encoding="utf-8")
            index = root / "index.json"
            index.write_text("original", encoding="utf-8")
            with patch.object(ingest, "CORPUS", corpus), patch.object(rag, "INDEX_PATH", index):
                with self.assertRaises(rag.RagError):
                    ingest.build_index()
            self.assertEqual(index.read_text(encoding="utf-8"), "original")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_invalid_input_returns_400(self):
        for payload in ({}, {"question": " "}, {"question": "Hola", "history": [{"role": "system", "content": "x"}]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/chat", json=payload).status_code, 400)

    def test_large_request_returns_json_error(self):
        response = self.client.post("/api/chat", json={"question": "x" * 33000})
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.json)

    def test_chat_and_explicit_service_error(self):
        with patch.object(rag, "answer", return_value={"answer": "Respuesta [1]", "sources": []}):
            response = self.client.post("/api/chat", json={"question": "Hola"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["answer"], "Respuesta [1]")
        with patch.object(rag, "answer", side_effect=rag.RagError("Ollama no disponible")):
            response = self.client.post("/api/chat", json={"question": "Hola"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json["error"], "Ollama no disponible")

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        response.close()


if __name__ == "__main__":
    unittest.main()
