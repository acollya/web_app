"""Create clinical_knowledge table for TCC/TRS knowledge base RAG.

Revision ID: 015
Revises: 014
Create Date: 2026-05-02

Tabela global (sem user_id) com chunks de conteúdo psicoeducativo em PT-BR
nas linhas TCC (Terapia Cognitivo-Comportamental) e TRS (Terapia Relacional
Sistêmica), além de conteúdos transversais de regulação emocional, crise,
relacionamento e autoconhecimento.

Características:
  - Embeddings 1536d (text-embedding-3-small) gerados pelo clinical_kb_service
    após a migração rodar (idempotente).
  - Recuperação global por similaridade cosseno + BM25 (RRF) — sem time decay.
  - lists=50 no IVFFlat; suficiente até alguns milhares de chunks.
  - GIN tsvector para BM25 (stemmer português).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# ── Revision ──────────────────────────────────────────────────────────────────

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Seed chunks ───────────────────────────────────────────────────────────────
# Cada tupla: (category, title, chunk_text)
# Conteúdo psicoeducativo em PT-BR, autoexplicativo, 3-6 frases por chunk.

_SEED_CHUNKS: list[tuple[str, str, str]] = [
    # ─── TCC ────────────────────────────────────────────────────────────────
    (
        "tcc",
        "Pensamentos automáticos",
        "Pensamentos automáticos são interpretações rápidas e involuntárias que surgem em "
        "resposta a situações do dia a dia, muitas vezes sem que percebamos. Eles costumam "
        "soar como verdades absolutas, mas frequentemente são leituras enviesadas ou "
        "incompletas da realidade. Identificar esses pensamentos é o primeiro passo da "
        "Terapia Cognitivo-Comportamental: pergunte-se 'o que passou pela minha cabeça "
        "agora?' nos momentos em que o humor mudar de forma intensa. Anotar o pensamento, "
        "a situação e a emoção ajuda a transformar conteúdo automático em material "
        "observável e trabalhável."
    ),
    (
        "tcc",
        "Distorções cognitivas comuns",
        "Distorções cognitivas são padrões sistemáticos de erro na forma como interpretamos "
        "o mundo. Entre as mais frequentes estão: catastrofização (esperar o pior), "
        "pensamento tudo-ou-nada (preto e branco, sem nuances), leitura mental (assumir o "
        "que o outro pensa), filtro mental (focar apenas no negativo) e personalização "
        "(atribuir a si mesmo a culpa por eventos externos). Reconhecer qual distorção "
        "está em ação cria distância crítica em relação ao pensamento e abre espaço para "
        "uma leitura mais equilibrada."
    ),
    (
        "tcc",
        "Reestruturação cognitiva",
        "A reestruturação cognitiva é o processo de examinar um pensamento automático e "
        "construir uma alternativa mais realista, e não simplesmente 'positiva'. O "
        "objetivo não é negar o que se sente, mas verificar se a interpretação cabe nos "
        "fatos disponíveis. Um caminho útil: escreva o pensamento, liste evidências a "
        "favor e contra, e formule uma versão revisada que considere todas as evidências. "
        "A nova frase precisa ser crível para você — caso contrário, não terá efeito "
        "emocional duradouro."
    ),
    (
        "tcc",
        "Questionamento socrático",
        "O questionamento socrático é uma técnica para examinar pensamentos por meio de "
        "perguntas guiadas, em vez de confrontá-los diretamente. Perguntas úteis incluem: "
        "'Qual é a evidência concreta a favor disso?', 'Existe outra forma de interpretar "
        "essa situação?', 'O que eu diria a um amigo querido na mesma situação?' e 'Qual "
        "o pior, o melhor e o cenário mais provável?'. Esse diálogo interno reduz a força "
        "de pensamentos rígidos e abre espaço para flexibilidade cognitiva."
    ),
    (
        "tcc",
        "Registro de pensamentos disfuncionais",
        "O Registro de Pensamentos Disfuncionais (RPD) é uma ferramenta clássica da TCC "
        "para mapear a relação entre situação, pensamento, emoção e comportamento. "
        "Estruture em colunas: o que aconteceu, qual pensamento veio à mente, quão "
        "intensa foi a emoção (0–100), qual evidência sustenta ou contradiz o pensamento "
        "e qual seria uma resposta mais equilibrada. Praticar o RPD por algumas semanas "
        "torna mais visíveis os padrões cognitivos que sustentam ansiedade, tristeza e "
        "raiva."
    ),
    (
        "tcc",
        "Ativação comportamental",
        "Ativação comportamental é uma estratégia central no manejo da depressão: agir "
        "antes de sentir vontade, em vez de esperar a vontade chegar. Quando o humor "
        "está baixo, tendemos a reduzir atividades — o que aprofunda o ciclo de apatia. "
        "Listar pequenas ações que historicamente geram prazer ou senso de competência "
        "(uma caminhada curta, arrumar um cômodo, ligar para alguém) e agendá-las como "
        "compromissos não-negociáveis quebra esse ciclo. O objetivo não é estar feliz "
        "para agir, mas agir para mover o humor."
    ),

    # ─── TRS ────────────────────────────────────────────────────────────────
    (
        "trs",
        "Padrões relacionais transgeracionais",
        "Na perspectiva relacional sistêmica, muitos sofrimentos individuais ganham "
        "sentido quando observados dentro da história da família. Padrões como "
        "superproteção, ausência emocional, papéis rígidos ou segredos podem se repetir "
        "ao longo de gerações sem que ninguém perceba conscientemente. Mapear quem "
        "ocupava qual papel na família de origem — quem cuidava, quem se isolava, quem "
        "era o 'forte' — ajuda a entender comportamentos atuais como heranças e não como "
        "defeitos pessoais."
    ),
    (
        "trs",
        "Ciclos de repetição em relacionamentos",
        "É comum perceber que vivemos versões parecidas do mesmo conflito em "
        "relacionamentos diferentes — com parceiros, chefes, amigos. Isso ocorre porque "
        "cada pessoa carrega um modelo interno do que é 'estar em relação', construído "
        "nas experiências mais antigas de vínculo. Identificar o ciclo (gatilho → "
        "reação → consequência relacional) é mais útil do que identificar culpados. A "
        "pergunta-chave passa a ser: 'que parte desse padrão depende de mim e posso "
        "começar a fazer diferente?'."
    ),
    (
        "trs",
        "Comunicação sistêmica",
        "Na visão sistêmica, mensagens não existem isoladas: sempre há quem fala, quem "
        "escuta, e o contexto que dá sentido à mensagem. Conflitos frequentemente "
        "surgem porque o conteúdo dito (o 'o quê') diverge da relação implícita (o "
        "'como'). Antes de discutir o tema, vale nomear a relação: 'estou me sentindo "
        "afastado de você e preciso falar sobre algo'. Esse cuidado prévio costuma "
        "transformar discussões repetitivas em conversas mais produtivas."
    ),
    (
        "trs",
        "Contexto familiar e sintoma individual",
        "A TRS sustenta que sintomas individuais — como ansiedade, queda de desempenho "
        "ou dificuldade nos vínculos — frequentemente sinalizam tensões no sistema "
        "familiar como um todo. A pessoa que apresenta o sintoma não é necessariamente "
        "'a doente', mas muitas vezes a mais sensível ao desequilíbrio coletivo. Olhar "
        "o sintoma como mensagem sistêmica não retira a responsabilidade do cuidado "
        "individual, mas amplia o leque de intervenções possíveis."
    ),
    (
        "trs",
        "Triangulações familiares",
        "Triangulação ocorre quando duas pessoas em conflito envolvem uma terceira "
        "para aliviar a tensão entre elas — como filhos colocados no meio de discussões "
        "do casal. O alívio é momentâneo, mas o padrão impede que a dupla original "
        "resolva o que precisa ser resolvido. Reconhecer triangulações em que se foi "
        "colocado historicamente é libertador: permite recusar gentilmente o papel de "
        "intermediário e devolver o conflito a quem ele pertence."
    ),
    (
        "trs",
        "Lealdades invisíveis",
        "Lealdades invisíveis são compromissos inconscientes com a família de origem "
        "que continuam ativos na vida adulta, muitas vezes sabotando escolhas que "
        "parecem livres. Por exemplo, alguém pode evitar prosperar profissionalmente "
        "para não 'ultrapassar' os pais, ou repetir relacionamentos infelizes para não "
        "se diferenciar de uma matriarca sofredora. Tornar essas lealdades conscientes "
        "permite honrá-las simbolicamente sem precisar repetir o sofrimento."
    ),

    # ─── REGULAÇÃO EMOCIONAL ────────────────────────────────────────────────
    (
        "regulacao",
        "Respiração diafragmática",
        "A respiração diafragmática ativa o sistema nervoso parassimpático e reduz a "
        "intensidade de respostas ansiosas em poucos minutos. Sente-se com a coluna "
        "apoiada, coloque uma mão sobre o abdômen e inspire pelo nariz contando até 4, "
        "sentindo a barriga se expandir; segure por 2 e expire pela boca contando até "
        "6. O ponto-chave é a expiração ser mais longa que a inspiração — é isso que "
        "sinaliza segurança ao corpo. Cinco minutos diários, fora de momentos de "
        "crise, fortalecem a habilidade quando você mais precisa."
    ),
    (
        "regulacao",
        "Ancoragem sensorial 5-4-3-2-1",
        "A técnica 5-4-3-2-1 traz a atenção de volta ao presente quando a mente está "
        "espiralando em ansiedade ou dissociação. Olhe ao redor e identifique: 5 "
        "coisas que você consegue ver, 4 coisas que pode tocar, 3 sons que escuta, 2 "
        "cheiros perceptíveis e 1 sabor na boca. Vá lentamente, nomeando cada item. "
        "O objetivo não é distrair-se da emoção, mas reconectar-se ao corpo e ao "
        "ambiente, recuperando a sensação de estar no aqui e agora."
    ),
    (
        "regulacao",
        "Tolerância ao sofrimento",
        "Tolerância ao sofrimento é a capacidade de atravessar emoções intensas sem "
        "tomar atitudes que pioram a situação a longo prazo. A premissa é que dor é "
        "inevitável, mas o sofrimento adicional vem de como respondemos a ela. "
        "Estratégias úteis incluem: aceitar que o momento é difícil sem julgar a "
        "emoção, usar gelo nas mãos ou rosto para ativar o reflexo de mergulho, "
        "praticar atividade física breve e intensa, e adiar decisões importantes até "
        "o pico da crise passar."
    ),
    (
        "regulacao",
        "Janela de tolerância",
        "A janela de tolerância é a faixa em que conseguimos sentir, pensar e agir "
        "de forma integrada. Acima dela, entramos em hiperativação (ansiedade, raiva, "
        "agitação); abaixo, em hipoativação (entorpecimento, desconexão, paralisia). "
        "Aprender a reconhecer em qual estado se está é o primeiro passo para "
        "voltar à janela: hiperativação pede recursos calmantes (respiração lenta, "
        "ambientes silenciosos); hipoativação pede recursos energizantes (movimento, "
        "estímulos sensoriais, contato social). Não há estado 'errado', apenas "
        "estados que pedem cuidados diferentes."
    ),
    (
        "regulacao",
        "Nomear para domar",
        "Estudos de neurociência mostram que nomear uma emoção com precisão reduz "
        "sua intensidade no corpo — um fenômeno descrito como 'name it to tame it'. "
        "Em vez de dizer 'estou mal', tente: 'percebo medo de não dar conta', "
        "'percebo raiva por ter sido interrompido', 'percebo tristeza pela despedida'. "
        "Quanto mais granular a nomeação, mais o córtex pré-frontal se ativa e "
        "regula a amígdala. Construir um vocabulário emocional mais rico é uma das "
        "habilidades mais subestimadas de saúde mental."
    ),
    (
        "regulacao",
        "Movimento como regulação",
        "O corpo regula a mente tanto quanto a mente regula o corpo. Caminhar 10 "
        "minutos em ritmo moderado, alongar de forma consciente ou fazer "
        "polichinelos por 60 segundos altera bioquimicamente o estado emocional ao "
        "liberar endorfinas e reduzir cortisol. Em momentos de bloqueio, ansiedade "
        "alta ou apatia, o atalho mais confiável raramente é pensar — é mover o "
        "corpo primeiro, mesmo em pequena dose, e depois reavaliar como se sente."
    ),

    # ─── CRISE ──────────────────────────────────────────────────────────────
    (
        "crise",
        "Sinais de risco e quando buscar ajuda",
        "Alguns sinais indicam que é importante buscar apoio imediato de um "
        "profissional ou serviço de emergência: pensamentos persistentes de morte ou "
        "de se machucar, plano concreto para se ferir, sensação prolongada de que a "
        "vida não vale a pena, isolamento extremo ou perda total de funcionalidade. "
        "Esses sinais não significam fraqueza — significam que o sofrimento "
        "ultrapassou o que se pode atravessar sozinho. Buscar ajuda nessa hora é um "
        "ato de cuidado, não de derrota."
    ),
    (
        "crise",
        "Centro de Valorização da Vida (CVV)",
        "O CVV é um serviço gratuito, sigiloso e disponível 24 horas para apoio "
        "emocional e prevenção do suicídio no Brasil. O atendimento é feito por "
        "voluntários treinados e pode ser acessado por telefone (188), chat, "
        "e-mail ou pessoalmente em postos de atendimento. Não é necessário estar "
        "em crise extrema para ligar — qualquer momento de angústia que pareça "
        "grande demais para enfrentar sozinho é motivo legítimo para buscar "
        "esse apoio."
    ),
    (
        "crise",
        "Plano de segurança pessoal",
        "Um plano de segurança é um documento simples, escrito antes de uma crise, "
        "que orienta o que fazer quando o sofrimento se intensifica. Inclui: "
        "sinais de alerta pessoais, estratégias de autocuidado que costumam "
        "funcionar, pessoas de confiança que podem ser acionadas, telefones de "
        "serviços de emergência (CVV 188, SAMU 192) e medidas para reduzir acesso a "
        "meios letais. Manter o plano acessível (geladeira, celular) garante que ele "
        "esteja disponível no momento em que a clareza está reduzida."
    ),
    (
        "crise",
        "Estratégias de adiamento em momentos de crise",
        "Em picos de sofrimento muito intenso, o objetivo não é resolver o "
        "problema — é atravessar a próxima hora sem agir contra si. Estratégias de "
        "adiamento incluem: combinar consigo mesmo esperar 24 horas antes de "
        "qualquer decisão drástica, retirar do alcance objetos que possam machucar, "
        "ir até um lugar público, ligar para alguém de confiança ou para o CVV. "
        "A intensidade de uma crise costuma ceder quando ganhamos tempo, mesmo "
        "que naquele instante pareça que ela durará para sempre."
    ),
    (
        "crise",
        "Rede de apoio em momentos difíceis",
        "Saber a quem recorrer em momentos difíceis é uma habilidade que pode ser "
        "construída antes da crise. Liste 3 a 5 pessoas que você confia o suficiente "
        "para procurar em diferentes tipos de necessidade: alguém para conversar, "
        "alguém para presença silenciosa, alguém para ajudar com tarefas práticas. "
        "Avise essas pessoas que elas estão na sua lista — a maioria responde com "
        "alívio e gratidão. Pedir ajuda costuma ser mais difícil do que oferecê-la, "
        "mas é uma das formas mais corajosas de cuidado consigo mesmo."
    ),

    # ─── RELACIONAMENTO ─────────────────────────────────────────────────────
    (
        "relacionamento",
        "Comunicação não-violenta",
        "A Comunicação Não-Violenta (CNV), proposta por Marshall Rosenberg, "
        "estrutura conversas difíceis em quatro passos: observação dos fatos sem "
        "julgamento, expressão do sentimento gerado, identificação da necessidade "
        "por trás do sentimento e formulação de um pedido concreto. Por exemplo: "
        "'quando você não respondeu minhas mensagens ontem (observação), me senti "
        "ansioso (sentimento) porque preciso saber que estamos bem (necessidade). "
        "Você pode me avisar quando estiver indisponível? (pedido)'. Esse formato "
        "reduz defesas e aumenta a chance de ser ouvido de fato."
    ),
    (
        "relacionamento",
        "Limites saudáveis",
        "Limites são os contornos que definem o que é aceitável e o que não é em "
        "uma relação. Estabelecer limites não é punir o outro, é informá-lo sobre "
        "como você precisa ser tratado para que o vínculo continue saudável. Um "
        "limite eficaz é específico ('não consigo conversar sobre isso quando você "
        "grita comigo'), realista de sustentar e seguido de uma consequência "
        "coerente caso seja desrespeitado. Sentir culpa ao impor limites é comum, "
        "mas a culpa não é evidência de que o limite seja errado."
    ),
    (
        "relacionamento",
        "Conflitos saudáveis em relacionamentos",
        "Conflitos não são sinal de que um relacionamento vai mal — são sinal de "
        "que duas pessoas distintas estão se relacionando de fato. O que diferencia "
        "casais saudáveis não é a ausência de discussões, mas a forma como reparam "
        "depois delas. Estratégias úteis: nomear o conflito como problema "
        "compartilhado e não como disputa pessoal, fazer pausas quando a ativação "
        "fisiológica passa de certo nível, voltar à conversa em outro momento e "
        "reconhecer abertamente a parcela própria de responsabilidade."
    ),
    (
        "relacionamento",
        "Escuta ativa",
        "Escutar ativamente é diferente de esperar a vez de falar. Envolve atenção "
        "plena ao que o outro diz, parafrasear o que entendeu para confirmar a "
        "compreensão e nomear o sentimento percebido antes de oferecer opinião ou "
        "solução. Frases como 'deixa ver se entendi…' ou 'parece que você está se "
        "sentindo… é isso?' transformam conversas. Muitas vezes, o que o outro "
        "precisa não é da sua resposta, mas da experiência genuína de se sentir "
        "compreendido."
    ),
    (
        "relacionamento",
        "Apego e estilos vinculares",
        "Os estilos de apego — seguro, ansioso, evitativo e desorganizado — "
        "descrevem padrões aprendidos cedo sobre como nos conectamos com pessoas "
        "próximas. Estilos ansiosos tendem a buscar muita proximidade e temer "
        "abandono; evitativos tendem a se distanciar quando a intimidade aumenta. "
        "Identificar o próprio padrão não é se rotular, mas ganhar consciência: "
        "estilos de apego não são fixos e podem se tornar mais seguros em "
        "relacionamentos que ofereçam previsibilidade, validação e disponibilidade "
        "consistente."
    ),

    # ─── AUTOCONHECIMENTO ──────────────────────────────────────────────────
    (
        "autoconhecimento",
        "Valores pessoais",
        "Valores são os princípios que dão direção à vida — não objetivos a "
        "alcançar, mas modos de viver. Diferentes de metas, valores nunca são "
        "concluídos: 'ser um pai presente' ou 'cultivar honestidade nas relações' "
        "são compromissos que se renovam diariamente. Em momentos de confusão, "
        "perguntar 'que tipo de pessoa eu quero ser nesta situação?' costuma "
        "trazer mais clareza do que perguntar 'o que eu deveria fazer?'. Decisões "
        "alinhadas a valores tendem a sustentar bem-estar mesmo quando os "
        "resultados externos não são os esperados."
    ),
    (
        "autoconhecimento",
        "Autocompaixão",
        "Autocompaixão é tratar a si mesmo, especialmente nos momentos difíceis, "
        "com o mesmo cuidado que dispensaria a um amigo querido. Tem três "
        "componentes: bondade consigo (em vez de autocrítica severa), reconhecer "
        "que sofrer faz parte da experiência humana (em vez de se sentir isolado) "
        "e mindfulness (em vez de identificação total com a dor). Ao contrário do "
        "que se teme, autocompaixão não enfraquece a motivação — pessoas mais "
        "compassivas consigo se recuperam mais rápido de fracassos e tomam mais "
        "responsabilidade pelos próprios erros."
    ),
    (
        "autoconhecimento",
        "Mindfulness básico",
        "Mindfulness é a prática de estar presente com o que está acontecendo, "
        "interna e externamente, sem julgamento. Não significa esvaziar a mente "
        "ou estar relaxado o tempo todo — significa notar pensamentos e "
        "sensações como eventos que aparecem e passam, em vez de ser arrastado "
        "por eles. Uma prática inicial simples: dedique 3 minutos a observar a "
        "respiração, e cada vez que perceber a mente vagando, nomeie 'pensando' "
        "e volte gentilmente à respiração. O músculo da atenção se fortalece "
        "exatamente nesse retorno, não em manter o foco perfeito."
    ),
    (
        "autoconhecimento",
        "Identidade e múltiplas partes",
        "Não somos uma coisa só: convivemos com diferentes partes internas — uma "
        "que quer descansar e outra que cobra produtividade, uma que deseja "
        "intimidade e outra que teme ser vulnerável. Tratar essas partes como "
        "inimigas costuma intensificar conflitos internos. Uma postura mais "
        "fértil é reconhecer cada parte como portadora de uma intenção "
        "protetora, mesmo quando a estratégia é desadaptativa hoje. Perguntar "
        "'o que essa parte está tentando proteger em mim?' transforma luta "
        "interna em diálogo."
    ),
    (
        "autoconhecimento",
        "Diário reflexivo como prática",
        "Escrever sobre o que se vive transforma experiência bruta em "
        "experiência integrada. Pesquisas mostram que escrita expressiva regular "
        "reduz sintomas de ansiedade e depressão e melhora a qualidade do sono. "
        "Não há fórmula única: pode ser narrativa do dia, lista do que foi "
        "difícil e do que foi bom, perguntas guiadas ('o que mais me tocou hoje?', "
        "'o que aprendi sobre mim?') ou cartas que nunca serão enviadas. O ganho "
        "vem da consistência, não da extensão de cada texto."
    ),
    (
        "autoconhecimento",
        "Aceitação radical",
        "Aceitação radical é reconhecer plenamente a realidade tal como ela é, "
        "mesmo quando dolorosa, em vez de gastar energia lutando contra fatos "
        "que não podem ser mudados. Aceitar não é concordar, gostar ou se "
        "resignar — é parar de adicionar sofrimento ao sofrimento por meio da "
        "recusa. Frases como 'isto é o que está acontecendo agora' ou 'não "
        "escolhi isto, mas é o que há' criam espaço interno para responder de "
        "forma mais sábia, em vez de apenas reagir."
    ),
    (
        "autoconhecimento",
        "Senso de propósito no cotidiano",
        "Propósito não precisa ser uma grande missão de vida para gerar "
        "bem-estar — pode ser uma intenção pequena que orienta o dia, como "
        "'hoje quero estar mais presente com meus filhos' ou 'quero fazer meu "
        "trabalho com mais cuidado'. Estabelecer uma intenção breve pela manhã "
        "e revisitá-la antes de dormir cria coerência entre o que se valoriza e "
        "o que se faz. Esse alinhamento mínimo, repetido, é um dos preditores "
        "mais robustos de satisfação com a vida ao longo do tempo."
    ),
]


# ── Upgrade ───────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # Garantia de extensão (já criada em migrações anteriores; idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. Tabela
    op.create_table(
        "clinical_knowledge",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default="internal"),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. Índice IVFFlat (cosine) — embeddings ainda nulos no momento da migração;
    #    o índice será efetivo após embed_all_pending() rodar.
    op.execute(
        """
        CREATE INDEX idx_clinical_knowledge_embedding
        ON clinical_knowledge
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
        """
    )

    # 3. tsvector gerado + GIN para BM25 (stemmer português)
    op.execute(
        """
        ALTER TABLE clinical_knowledge
        ADD COLUMN ts_content tsvector
        GENERATED ALWAYS AS (
            to_tsvector('portuguese', coalesce(title, '') || ' ' || chunk_text)
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_clinical_knowledge_ts_content "
        "ON clinical_knowledge USING gin(ts_content)"
    )

    # 4. Índice por categoria (filtros opcionais futuros)
    op.create_index(
        "idx_clinical_knowledge_category",
        "clinical_knowledge",
        ["category"],
    )

    # 5. Seed dos chunks iniciais
    table = sa.table(
        "clinical_knowledge",
        sa.column("category", sa.Text),
        sa.column("title", sa.Text),
        sa.column("chunk_text", sa.Text),
        sa.column("source", sa.Text),
    )
    op.bulk_insert(
        table,
        [
            {
                "category": cat,
                "title": title,
                "chunk_text": chunk,
                "source": "internal",
            }
            for cat, title, chunk in _SEED_CHUNKS
        ],
    )


# ── Downgrade ─────────────────────────────────────────────────────────────────


def downgrade() -> None:
    op.drop_index("idx_clinical_knowledge_category", table_name="clinical_knowledge")
    op.execute("DROP INDEX IF EXISTS idx_clinical_knowledge_ts_content")
    op.execute("ALTER TABLE clinical_knowledge DROP COLUMN IF EXISTS ts_content")
    op.execute("DROP INDEX IF EXISTS idx_clinical_knowledge_embedding")
    op.drop_table("clinical_knowledge")
