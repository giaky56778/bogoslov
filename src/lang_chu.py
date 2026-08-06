ms2color = {
    "S": "#90AA00",
    "B": "#00AA90",
    "M": "#0090AA",
    "Z": "#9000AA",
}

ms2source = {
    "S": "syntacticus.psalter.sinai",
    "B": "oxford.psalter.bologna",
    "M": "syntacticus.gospel.marianus",
    "Z": "syntacticus.gospel.zographensis",
}

udpipe_model = "old_church_slavonic-proiel-ud-2.15-241121"

# This is used for DB generation only. Runtime checks models available in memory
strans_models = [
    "uaritm/multilingual_en_uk_pl_ru",  # 768
    "pouxie/LaBSE-en-ru-bviolet",  # 768
    #"siberian-lang-lab/evenki-russian-parallel-corpora",  # 768
    #"Diiiann/ru_oss",  # 768
    #"DiTy/bi-encoder-russian-msmarco",  # 768
    "sentence-transformers/LaBSE",  # 768
]

strans_toolpit={
    "multilingual_en_uk_pl_ru": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque porta, nunc quis lacinia aliquet, magna neque porttitor elit, vitae pulvinar ipsum turpis in sem. In ut maximus mauris. Morbi ligula velit, mattis ac tortor id, lacinia imperdiet eros. Cras dapibus non mauris quis luctus. Sed rutrum porttitor odio ut congue. Morbi pulvinar risus varius faucibus convallis. Phasellus gravida ante at ligula iaculis tristique. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Curabitur pellentesque quam in bibendum rhoncus. ",
    "LaBSE-en-ru-bviolet": "In vestibulum eleifend eros. Fusce volutpat sapien suscipit magna consectetur, congue auctor libero finibus. Quisque tortor erat, finibus sed tempus sollicitudin, vestibulum vitae leo. Vivamus at convallis mauris. Nullam tempor velit nisl. Nullam et elit tincidunt dui accumsan molestie eget at purus. Vestibulum pulvinar sodales leo, non varius metus imperdiet sit amet. Donec id mi nec nibh porta mollis. ",
    #"evenki-russian-parallel-corpora": "Integer efficitur nibh augue. Morbi diam orci, aliquet ut nulla a, lacinia tempor est. Proin vel vestibulum nisi, et congue mauris. Integer euismod massa dui, quis pretium ex faucibus eu. Nam auctor, dolor eu imperdiet fringilla, dui massa dictum neque, id fringilla ex eros eu purus. Maecenas eget ullamcorper dui, vitae lacinia lacus. Nulla mollis, metus sit amet finibus ultricies, elit lacus mattis est, sed venenatis mauris ex eget nunc. Mauris dictum tincidunt orci eleifend posuere. Nunc fringilla laoreet iaculis. Fusce vitae felis suscipit, semper neque in, congue justo. Donec a sapien dolor. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam erat volutpat. ",
    #"ru_oss": "Praesent cursus imperdiet blandit. Phasellus non ex luctus, condimentum eros efficitur, ornare diam. Duis ex magna, convallis a venenatis sed, venenatis non dui. Mauris aliquet, tellus ut cursus tristique, urna leo interdum tortor, ac hendrerit dui sem eget lectus. Morbi vulputate congue urna, vel bibendum nunc mattis sed. Curabitur eu euismod magna. Sed at lectus bibendum, ornare justo id, venenatis ante. Cras vulputate non dui nec blandit. Vestibulum blandit dapibus erat, eget bibendum justo aliquam a. Donec fringilla at tortor id sollicitudin. ",
    #"bi-encoder-russian-msmarco": "Nullam in maximus justo. Praesent vitae convallis ligula, et porttitor purus. Donec a sapien mi. Aliquam erat volutpat. Ut tempus porta lectus placerat pharetra. Fusce vitae pellentesque lectus. Suspendisse scelerisque metus in ornare luctus. Etiam in mi quis massa venenatis vestibulum sed ac risus. Proin rutrum velit purus, a tristique neque tristique ut. Suspendisse id quam risus. Nulla eu lorem orci. Etiam consequat turpis et tellus dignissim dapibus. Phasellus vehicula sapien magna, a scelerisque dolor consequat ut. Maecenas nec congue quam. ",
    "LaBSE":"In pulvinar mi at risus tincidunt mollis. Nullam posuere libero nisi, vehicula ornare justo auctor ut. Donec pretium eros ac lectus convallis maximus. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aenean eget arcu dolor. Suspendisse potenti. Sed lacus ante, porta eu consectetur eget, faucibus hendrerit est. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Suspendisse faucibus sollicitudin laoreet. Sed tincidunt sodales mi a tempus. Curabitur ut tempor metus. Nulla dapibus viverra erat sed ornare. Proin at efficitur augue. Sed dignissim ex semper ante molestie semper. Curabitur hendrerit elementum velit, non semper nisi pretium sit amet. "
}

examples = [
    "богомъ",
    "въса землꙗ да поклонит ти се и поеть тебе",
    "Приде же въ градъ самарьскъ",
    "Не осѫждаите да не осѫждени бѫдете",
]
