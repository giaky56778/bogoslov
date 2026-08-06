ms2color = {
    "O": "#90AA00",
}

ms2source = {
    "O": "syntacticus.gospel.octava",
}

udpipe_model = "greek-gdt-ud-2.17-251125"

# This is used for DB generation only. Runtime checks models available in memory
strans_models = [
    "sentence-transformers/LaBSE",  # 768
    "intfloat/multilingual-e5-base",  # 768
    # "nomic-ai/nomic-embed-text-v2-moe", #768
    # "antoinelouis/colbert-xm",  # 768
    # "setu4993/LEALLA-small", #192
    # "setu4993/LEALLA-base", #192
    "bowphs/SPhilBerta",  # 768
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # 768
]

strans_toolpit={
    "LaBSE": "In vestibulum eleifend eros. Fusce volutpat sapien suscipit magna consectetur, congue auctor libero finibus. Quisque tortor erat, finibus sed tempus sollicitudin, vestibulum vitae leo. Vivamus at convallis mauris. Nullam tempor velit nisl. Nullam et elit tincidunt dui accumsan molestie eget at purus. Vestibulum pulvinar sodales leo, non varius metus imperdiet sit amet. Donec id mi nec nibh porta mollis. ",
    "paraphrase-multilingual-mpnet-base-v2": "Integer efficitur nibh augue. Morbi diam orci, aliquet ut nulla a, lacinia tempor est. Proin vel vestibulum nisi, et congue mauris. Integer euismod massa dui, quis pretium ex faucibus eu. Nam auctor, dolor eu imperdiet fringilla, dui massa dictum neque, id fringilla ex eros eu purus. Maecenas eget ullamcorper dui, vitae lacinia lacus. Nulla mollis, metus sit amet finibus ultricies, elit lacus mattis est, sed venenatis mauris ex eget nunc. Mauris dictum tincidunt orci eleifend posuere. Nunc fringilla laoreet iaculis. Fusce vitae felis suscipit, semper neque in, congue justo. Donec a sapien dolor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam erat volutpat. ",
    "SPhilBerta": "Praesent cursus imperdiet blandit. Phasellus non ex luctus, condimentum eros efficitur, ornare diam. Duis ex magna, convallis a venenatis sed, venenatis non dui. Mauris aliquet, tellus ut cursus tristique, urna leo interdum tortor, ac hendrerit dui sem eget lectus. Morbi vulputate congue urna, vel bibendum nunc mattis sed. Curabitur eu euismod magna. Sed at lectus bibendum, ornare justo id, venenatis ante. Cras vulputate non dui nec blandit. Vestibulum blandit dapibus erat, eget bibendum justo aliquam a. Donec fringilla at tortor id sollicitudin. ",
    "multilingual-e5-base": "Nullam in maximus justo. Praesent vitae convallis ligula, et porttitor purus. Donec a sapien mi. Aliquam erat volutpat. Ut tempus porta lectus placerat pharetra. Fusce vitae pellentesque lectus. Suspendisse scelerisque metus in ornare luctus. Etiam in mi quis massa venenatis vestibulum sed ac risus. Proin rutrum velit purus, a tristique neque tristique ut. Suspendisse id quam risus. Nulla eu lorem orci. Etiam consequat turpis et tellus dignissim dapibus. Phasellus vehicula sapien magna, a scelerisque dolor consequat ut. Maecenas nec congue quam. "
}

examples = [
    "Ἰατρέ, θεράπευσον σεαυτόν",
    "Ἰησοῦς Χριστὸς Θεοῦ Υἱὸς Σωτήρ",
    "ναὶ ναί, οὒ οὔ",
    "Σὺν Ἀθηνᾷ καὶ χεῖρα κίνει",
    "Ego sum via et veritas et vita",
    "βασιλεία τῶν οὐρανῶν",
    "υἱὸς μονογενής",
]
