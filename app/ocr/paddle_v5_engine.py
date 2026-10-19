"""PaddleOCR 3.x execution bridge; raw SDK values stay inside the Provider."""


class PaddleV5Engine:
    engine_version = 'ppocrv5-sdk3'

    def __init__(self, *, lang='korean', use_gpu=False, use_angle_cls=False,
                 show_log=False, det_limit_side_len=1920):
        from paddleocr import PaddleOCR

        if lang != 'korean':
            raise ValueError('paddle_v5_language_not_supported')
        self.device = 'gpu:0' if use_gpu else 'cpu'
        self.pipeline = PaddleOCR(lang=lang, ocr_version='PP-OCRv5', device=self.device,
            use_doc_orientation_classify=False, use_doc_unwarping=False,
            use_textline_orientation=use_angle_cls, text_det_limit_side_len=det_limit_side_len,
            text_det_limit_type='max', enable_mkldnn=False, cpu_threads=4)
        self.recognizer = None

    def ocr(self, source, *, det=True, cls=False):
        if not det:
            if self.recognizer is None:
                from paddleocr import TextRecognition

                self.recognizer = TextRecognition(model_name='korean_PP-OCRv5_mobile_rec',
                    device=self.device, enable_mkldnn=False, cpu_threads=4)
            return [[(row['rec_text'], float(row['rec_score']))
                     for row in self.recognizer.predict(source)]]
        return [
            [[box.tolist() if hasattr(box, 'tolist') else box, (text, float(score))]
             for box, text, score in zip(row['rec_polys'], row['rec_texts'], row['rec_scores'], strict=True)]
            for row in self.pipeline.predict(source, use_textline_orientation=cls)
        ]
