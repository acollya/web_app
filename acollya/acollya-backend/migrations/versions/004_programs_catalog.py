"""Create programs and chapters catalog tables with initial seed data

Revision ID: 004
Revises: 003
Create Date: 2026-03-31

Seed data: 5 evidence-based self-care programs in PT-BR.
  1. Mindfulness para Iniciantes    (7 chapters,  beginner,  free)
  2. Gestao de Ansiedade            (10 chapters, intermediate, premium)
  3. Autoestima e Confianca         (10 chapters, intermediate, premium)
  4. Relacionamentos Saudaveis      (8 chapters,  intermediate, premium)
  5. Sono Reparador                 (7 chapters,  beginner,  free)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── programs table ────────────────────────────────────────────────────────
    op.create_table(
        "programs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Text(), nullable=False),
        sa.Column("cover_image_key", sa.Text(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_programs_category", "programs", ["category"])
    op.create_index("idx_programs_sort_order", "programs", ["sort_order"])

    # ── chapters table ────────────────────────────────────────────────────────
    op.create_table(
        "chapters",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("program_id", sa.Text(),
                  sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False, server_default="'text'"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_chapters_program_id", "chapters", ["program_id"])
    op.create_index("idx_chapters_order", "chapters", ["program_id", "order"])

    # ── Seed programs ─────────────────────────────────────────────────────────
    programs_table = sa.table(
        "programs",
        sa.column("id", sa.Text),
        sa.column("title", sa.Text),
        sa.column("description", sa.Text),
        sa.column("category", sa.Text),
        sa.column("duration_days", sa.Integer),
        sa.column("difficulty", sa.Text),
        sa.column("cover_image_key", sa.Text),
        sa.column("is_premium", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(programs_table, [
        {
            "id": "mindfulness-iniciantes",
            "title": "Mindfulness para Iniciantes",
            "description": "Aprenda tecnicas de atencao plena para reduzir o estresse e aumentar o bem-estar no dia a dia.",
            "category": "mindfulness",
            "duration_days": 7,
            "difficulty": "beginner",
            "cover_image_key": "programs/mindfulness.jpg",
            "is_premium": False,
            "sort_order": 1,
        },
        {
            "id": "gestao-ansiedade",
            "title": "Gestao de Ansiedade",
            "description": "Ferramentas praticas baseadas em TCC para identificar e lidar com a ansiedade do cotidiano.",
            "category": "anxiety",
            "duration_days": 14,
            "difficulty": "intermediate",
            "cover_image_key": "programs/anxiety.jpg",
            "is_premium": True,
            "sort_order": 2,
        },
        {
            "id": "autoestima-confianca",
            "title": "Autoestima e Confianca",
            "description": "Uma jornada para reconhecer seu valor, superar a autocritica e construir uma imagem positiva de si mesmo.",
            "category": "self-esteem",
            "duration_days": 14,
            "difficulty": "intermediate",
            "cover_image_key": "programs/self-esteem.jpg",
            "is_premium": True,
            "sort_order": 3,
        },
        {
            "id": "relacionamentos-saudaveis",
            "title": "Relacionamentos Saudaveis",
            "description": "Desenvolva habilidades de comunicacao, limites saudaveis e conexoes mais autenticas.",
            "category": "relationships",
            "duration_days": 10,
            "difficulty": "intermediate",
            "cover_image_key": "programs/relationships.jpg",
            "is_premium": True,
            "sort_order": 4,
        },
        {
            "id": "sono-reparador",
            "title": "Sono Reparador",
            "description": "Tecnicas de higiene do sono e relaxamento para melhorar a qualidade do seu descanso.",
            "category": "sleep",
            "duration_days": 7,
            "difficulty": "beginner",
            "cover_image_key": "programs/sleep.jpg",
            "is_premium": False,
            "sort_order": 5,
        },
    ])

    # ── Seed chapters ─────────────────────────────────────────────────────────
    chapters_table = sa.table(
        "chapters",
        sa.column("id", sa.Text),
        sa.column("program_id", sa.Text),
        sa.column("order", sa.Integer),
        sa.column("title", sa.Text),
        sa.column("content", sa.Text),
        sa.column("content_type", sa.Text),
        sa.column("duration_minutes", sa.Integer),
    )

    # ── Program 1: Mindfulness para Iniciantes (7 chapters) ──────────────────
    op.bulk_insert(chapters_table, [
        {
            "id": "mindfulness-1-1",
            "program_id": "mindfulness-iniciantes",
            "order": 1,
            "title": "O que e Mindfulness?",
            "content": (
                "## O que e Mindfulness?\n\n"
                "Mindfulness e a pratica de prestar atencao intencional ao momento presente, "
                "sem julgamentos. Nao se trata de esvaziar a mente, mas de observar seus "
                "pensamentos e sentimentos como um espectador curioso.\n\n"
                "### Por que praticar?\n"
                "- Reduz o estresse e a ansiedade\n"
                "- Melhora o foco e a concentracao\n"
                "- Aumenta a autoconsciencia\n"
                "- Promove maior bem-estar emocional\n\n"
                "### Exercicio de hoje\n"
                "Respire fundo 3 vezes. Em cada inspiracao, note as sensacoes no seu corpo. "
                "Na expiracao, solte qualquer tensao. Isso ja e mindfulness."
            ),
            "content_type": "text",
            "duration_minutes": 5,
        },
        {
            "id": "mindfulness-1-2",
            "program_id": "mindfulness-iniciantes",
            "order": 2,
            "title": "Respiracao Consciente",
            "content": (
                "## Respiracao Consciente\n\n"
                "A respiracao e a ancora do mindfulness — ela sempre esta no presente.\n\n"
                "### Tecnica 4-7-8\n"
                "1. **Inspire** pelo nariz contando ate 4\n"
                "2. **Segure** o ar contando ate 7\n"
                "3. **Expire** pela boca contando ate 8\n\n"
                "Repita 4 vezes. Esta tecnica ativa o sistema nervoso parassimpatico, "
                "promovendo relaxamento imediato.\n\n"
                "### Pratica diaria\n"
                "Reserve 5 minutos hoje para praticar apenas observando sua respiracao. "
                "Quando a mente vagar, gentilmente retorne a atencao para o ar."
            ),
            "content_type": "text",
            "duration_minutes": 7,
        },
        {
            "id": "mindfulness-1-3",
            "program_id": "mindfulness-iniciantes",
            "order": 3,
            "title": "Observando Pensamentos",
            "content": (
                "## Observando Pensamentos\n\n"
                "Voce nao e seus pensamentos. Voce e quem os observa.\n\n"
                "### A metafora do ceu e das nuvens\n"
                "Imagine que sua consciencia e o ceu — vasto e sempre presente. "
                "Os pensamentos sao nuvens que passam. Algumas sao escuras e pesadas, "
                "outras leves e passageiras. O ceu nao e afetado pelas nuvens.\n\n"
                "### Exercicio: Rotulando pensamentos\n"
                "Quando surgir um pensamento, mentalmente rotule-o:\n"
                "- 'Isso e um pensamento de preocupacao'\n"
                "- 'Isso e um julgamento'\n"
                "- 'Isso e uma lembranca'\n\n"
                "O simples ato de nomear cria distancia saudavel entre voce e o pensamento."
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
        {
            "id": "mindfulness-1-4",
            "program_id": "mindfulness-iniciantes",
            "order": 4,
            "title": "Escaneamento Corporal",
            "content": (
                "## Escaneamento Corporal (Body Scan)\n\n"
                "O escaneamento corporal reconecta voce com as sensacoes fisicas do presente.\n\n"
                "### Como praticar\n"
                "Deite-se confortavelmente. Comece pelos dedos dos pes e suba lentamente "
                "ate o topo da cabeca, passando por cada parte do corpo:\n\n"
                "- Note sensacoes (calor, tensao, formigamento, relaxamento)\n"
                "- Nao tente mudar nada — apenas observe\n"
                "- Se encontrar tensao, respire em direcao a ela\n\n"
                "### Duracao\n"
                "Comece com 10 minutos. Com a pratica, voce pode estender para 20-30 minutos."
            ),
            "content_type": "text",
            "duration_minutes": 10,
        },
        {
            "id": "mindfulness-1-5",
            "program_id": "mindfulness-iniciantes",
            "order": 5,
            "title": "Mindfulness no Cotidiano",
            "content": (
                "## Mindfulness no Cotidiano\n\n"
                "Voce nao precisa meditar para praticar mindfulness. Qualquer atividade "
                "pode ser uma oportunidade de presenca plena.\n\n"
                "### Atividades mindful\n"
                "**Ao comer:** Observe cores, texturas, aromas. Mastigue devagar.\n\n"
                "**Ao caminhar:** Sinta o contato dos pes com o chao. Observe o ambiente.\n\n"
                "**Ao lavar a louca:** Sinta a temperatura da agua, a textura dos objetos.\n\n"
                "**Ao ouvir musica:** Ouva apenas a musica — sem multitarefa.\n\n"
                "### Desafio de hoje\n"
                "Escolha uma atividade rotineira e faca-a com atencao plena."
            ),
            "content_type": "text",
            "duration_minutes": 6,
        },
        {
            "id": "mindfulness-1-6",
            "program_id": "mindfulness-iniciantes",
            "order": 6,
            "title": "Lidando com Distracao",
            "content": (
                "## Lidando com Distracao\n\n"
                "A mente que divaga nao e uma mente falha — e uma mente humana. "
                "A pratica e notar a distracao e retornar, sem autocritica.\n\n"
                "### O muscle de retorno\n"
                "Cada vez que voce percebe que a mente foi embora e a traz de volta, "
                "voce esta fortalecendo seu 'musculo' de atencao. Isso e a pratica.\n\n"
                "### Obstaculos comuns\n"
                "- **'Nao consigo parar de pensar'** — Nao e o objetivo. O objetivo e observar.\n"
                "- **'Fico com sono'** — Experimente meditar sentado ou de olhos abertos.\n"
                "- **'Nao tenho tempo'** — 5 minutos ao acordar ja sao transformadores.\n\n"
                "### Pratica guiada\n"
                "Sente-se confortavelmente. Por 5 minutos, observe apenas a respiracao. "
                "Cada vez que a mente vagar, apenas retorne — sem julgamento."
            ),
            "content_type": "text",
            "duration_minutes": 7,
        },
        {
            "id": "mindfulness-1-7",
            "program_id": "mindfulness-iniciantes",
            "order": 7,
            "title": "Construindo uma Pratica Duradoura",
            "content": (
                "## Construindo uma Pratica Duradoura\n\n"
                "Parabens por completar os 7 dias! Agora o desafio e manter o que voce aprendeu.\n\n"
                "### Dicas para consistencia\n"
                "1. **Hora fixa:** Associe a pratica a um habito existente (cafe da manha, antes de dormir)\n"
                "2. **Comece pequeno:** 5 minutos todos os dias superam 1 hora uma vez por semana\n"
                "3. **Sem perfeicao:** Dias 'ruins' de meditacao ainda sao meditacao\n"
                "4. **Registro:** Anote como se sentiu antes e depois\n\n"
                "### Proximos passos\n"
                "- Explore o programa 'Gestao de Ansiedade' para aprofundar as tecnicas\n"
                "- Use o diario da Acollya para registrar suas praticas\n"
                "- Faca check-ins de humor para acompanhar seu progresso\n\n"
                "**Voce e capaz. Continue sua jornada.**"
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
    ])

    # ── Program 2: Gestao de Ansiedade (10 chapters) ─────────────────────────
    op.bulk_insert(chapters_table, [
        {
            "id": "ansiedade-2-1",
            "program_id": "gestao-ansiedade",
            "order": 1,
            "title": "Entendendo a Ansiedade",
            "content": (
                "## Entendendo a Ansiedade\n\n"
                "A ansiedade e uma resposta natural do corpo ao perigo percebido. "
                "O problema ocorre quando ela e ativada sem um perigo real.\n\n"
                "### A resposta luta-ou-fuga\n"
                "Quando seu cerebro percebe ameaca, libera adrenalina e cortisol:\n"
                "- Coracao acelera\n- Respiracao fica rapida\n- Musculos tensionam\n"
                "- Digestion fica lenta\n\n"
                "Isso e util num perigo real. Mas quando ativado pelo estresse cotidiano, "
                "gera sofrimento desnecessario.\n\n"
                "### Reflexao\n"
                "Quais situacoes costumam ativar sua ansiedade? "
                "Anote no seu diario hoje."
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
        {
            "id": "ansiedade-2-2",
            "program_id": "gestao-ansiedade",
            "order": 2,
            "title": "Identificando Gatilhos",
            "content": (
                "## Identificando Gatilhos\n\n"
                "Um gatilho e qualquer situacao, pensamento ou sensacao que dispara ansiedade.\n\n"
                "### Tipos de gatilhos\n"
                "**Externos:** situacoes sociais, prazos, conflitos, incertezas\n\n"
                "**Internos:** pensamentos catastroficos, memorias, sensacoes fisicas\n\n"
                "### Exercicio: Diario de gatilhos\n"
                "Por 3 dias, sempre que sentir ansiedade, registre:\n"
                "1. O que estava acontecendo?\n"
                "2. Qual pensamento surgiu?\n"
                "3. Qual sensacao fisica sentiu?\n"
                "4. O que fez em seguida?\n\n"
                "Padroes vao emergir. Conhecimento e poder."
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
        {
            "id": "ansiedade-2-3",
            "program_id": "gestao-ansiedade",
            "order": 3,
            "title": "Tecnica de Aterramento 5-4-3-2-1",
            "content": (
                "## Tecnica de Aterramento 5-4-3-2-1\n\n"
                "Quando a ansiedade pica, esta tecnica traz voce de volta ao presente.\n\n"
                "### Como fazer\n"
                "**5 coisas que voce VE** ao redor\n\n"
                "**4 coisas que voce pode TOCAR** — sinta as texturas\n\n"
                "**3 coisas que voce OUVE** — vozes, sons da rua, silencio\n\n"
                "**2 coisas que voce CHEIRA** — ou pode imaginar que cheiraria\n\n"
                "**1 coisa que voce PROVA** — ou lembra do gosto de algo\n\n"
                "### Por que funciona\n"
                "Engaja os sentidos no presente, interrompendo o loop ansioso "
                "que vive no passado ou futuro.\n\n"
                "### Pratica\n"
                "Faca agora, mesmo sem ansiedade. Isso treina o automatismo para usar "
                "quando precisar."
            ),
            "content_type": "text",
            "duration_minutes": 7,
        },
        {
            "id": "ansiedade-2-4",
            "program_id": "gestao-ansiedade",
            "order": 4,
            "title": "Reestruturacao Cognitiva",
            "content": (
                "## Reestruturacao Cognitiva\n\n"
                "Nossos pensamentos nao sao fatos. A TCC nos ensina a questiona-los.\n\n"
                "### Distorcoes cognitivas comuns\n"
                "- **Catastrofizacao:** 'Va ser terrivel'\n"
                "- **Leitura mental:** 'Sei que pensaram mal de mim'\n"
                "- **Generalizacao:** 'Isso sempre acontece comigo'\n"
                "- **Filtro mental:** So enxergar o negativo\n\n"
                "### As 3 perguntas da TCC\n"
                "Quando surgir um pensamento ansioso, pergunte:\n"
                "1. **Qual a evidencia real** de que isso vai acontecer?\n"
                "2. **Qual e a pior hipotese realista** (nao catastrofica)?\n"
                "3. **O que eu diria a um amigo** que tivesse esse pensamento?\n\n"
                "Com pratica, isso se torna automatico."
            ),
            "content_type": "text",
            "duration_minutes": 10,
        },
        {
            "id": "ansiedade-2-5",
            "program_id": "gestao-ansiedade",
            "order": 5,
            "title": "Respiracao Diafragmatica",
            "content": (
                "## Respiracao Diafragmatica\n\n"
                "A respiracao profunda ativa o sistema nervoso parassimpatico, "
                "o 'freio' natural da ansiedade.\n\n"
                "### Tecnica caixa (Box Breathing)\n"
                "Usada por soldados das forcas especiais e atletas de alto rendimento:\n\n"
                "1. Inspire pelo nariz: **4 segundos**\n"
                "2. Segure: **4 segundos**\n"
                "3. Expire pela boca: **4 segundos**\n"
                "4. Segure: **4 segundos**\n\n"
                "Repita por 4 ciclos.\n\n"
                "### Quando usar\n"
                "- Antes de situacoes ansiogenas (reunioes, apresentacoes)\n"
                "- Durante um ataque de panico\n"
                "- Para adormecer mais facilmente\n"
                "- Como rotina matinal de 2 minutos"
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
        {
            "id": "ansiedade-2-6",
            "program_id": "gestao-ansiedade",
            "order": 6,
            "title": "Exposicao Gradual",
            "content": (
                "## Exposicao Gradual\n\n"
                "Evitar o que nos causa ansiedade alimenta o ciclo ansioso. "
                "A exposicao gradual quebra esse ciclo.\n\n"
                "### O principio\n"
                "Cada vez que enfrentamos algo temido e sobrevivemos, o cerebro aprende "
                "'isso nao e perigoso'. A ansiedade diminui com a exposicao repetida.\n\n"
                "### Hierarquia de exposicao\n"
                "1. Anote situacoes ansiosas de 1 (pouco) a 10 (muito)\n"
                "2. Comece pela situacao com nota 3-4\n"
                "3. Enfrente-a ate a ansiedade reduzir naturalmente\n"
                "4. Suba para a proxima situacao\n\n"
                "### Importante\n"
                "Para ansiedade severa ou fobia, trabalhe com um psicologo. "
                "Esta tecnica e para ansiedade moderada do cotidiano."
            ),
            "content_type": "text",
            "duration_minutes": 9,
        },
        {
            "id": "ansiedade-2-7",
            "program_id": "gestao-ansiedade",
            "order": 7,
            "title": "O Papel do Corpo",
            "content": (
                "## O Papel do Corpo na Ansiedade\n\n"
                "Mente e corpo sao inseparaveis. Cuidar do corpo e cuidar da saude mental.\n\n"
                "### Fatores fisicos que amplificam a ansiedade\n"
                "- **Cafeina:** estimulante que mimetiza sintomas de ansiedade\n"
                "- **Privacao de sono:** aumenta a reatividade emocional\n"
                "- **Sedentarismo:** acumula tensao no corpo\n"
                "- **Hidratacao:** desidratacao causa confusao e nervosismo\n\n"
                "### O exercicio fisico como ansiolítico natural\n"
                "30 minutos de exercicio moderado 3x por semana reduz ansiedade tanto "
                "quanto medicamentos em estudos controlados. A razao: consome cortisol "
                "e libera endorfinas.\n\n"
                "### Desafio\n"
                "Esta semana, incorpore uma caminhada de 20 minutos ao dia."
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
        {
            "id": "ansiedade-2-8",
            "program_id": "gestao-ansiedade",
            "order": 8,
            "title": "Preocupacao Produtiva vs. Ruminacao",
            "content": (
                "## Preocupacao Produtiva vs. Ruminacao\n\n"
                "Nem toda preocupacao e inutil. Mas ha uma diferenca crucial.\n\n"
                "### Preocupacao produtiva\n"
                "- Tem foco em solucoes\n"
                "- Gera acao\n"
                "- Tem um fim natural\n\n"
                "### Ruminacao\n"
                "- Gira em loops repetitivos\n"
                "- Nao gera acao\n"
                "- Aumenta o sofrimento\n\n"
                "### Tecnica: Hora da preocupacao\n"
                "Designe 20 minutos por dia como sua 'hora de preocupar'. "
                "Quando uma preocupacao surgir fora desse horario, anote e addie. "
                "Na hora marcada, examine cada item: e algo que posso resolver? "
                "Se sim, planeje a acao. Se nao, pratique a aceitacao."
            ),
            "content_type": "text",
            "duration_minutes": 9,
        },
        {
            "id": "ansiedade-2-9",
            "program_id": "gestao-ansiedade",
            "order": 9,
            "title": "Aceitacao e Tolerancia a Incerteza",
            "content": (
                "## Aceitacao e Tolerancia a Incerteza\n\n"
                "Grande parte da ansiedade vem da intolerancia a incerteza. "
                "Queremos garantias que a vida nao pode dar.\n\n"
                "### O paradoxo do controle\n"
                "Quanto mais tentamos controlar o incontrolavel, mais ansiosos ficamos. "
                "A aceitacao nao e resignacao — e reconhecer o que esta e o que nao esta "
                "em nossas maos.\n\n"
                "### Circulo de controle\n"
                "Faca dois circulos:\n"
                "**Dentro:** O que posso controlar (minhas acoes, respostas, preparo)\n"
                "**Fora:** O que nao posso controlar (outros, o futuro, o passado)\n\n"
                "Concentre sua energia no circulo interno.\n\n"
                "### Pratica de aceitacao\n"
                "Quando surgir um pensamento ansioso sobre algo incerto, diga: "
                "'Isso esta fora do meu controle. Eu aceito a incerteza e foco no que posso fazer.'"
            ),
            "content_type": "text",
            "duration_minutes": 10,
        },
        {
            "id": "ansiedade-2-10",
            "program_id": "gestao-ansiedade",
            "order": 10,
            "title": "Construindo Resiliencia",
            "content": (
                "## Construindo Resiliencia\n\n"
                "Parabens por completar este programa! Resiliencia e uma habilidade, "
                "nao uma caracteristica inata.\n\n"
                "### O que voce aprendeu\n"
                "- Como a ansiedade funciona fisiologicamente\n"
                "- Seus gatilhos pessoais\n"
                "- Tecnicas de aterramento e respiracao\n"
                "- Reestruturacao cognitiva\n"
                "- Exposicao gradual\n"
                "- A diferenca entre ruminacao e preocupacao produtiva\n\n"
                "### Quando buscar apoio profissional\n"
                "Se a ansiedade estiver interferindo significativamente no trabalho, "
                "relacionamentos ou qualidade de vida, um psicologo pode ajudar muito. "
                "Terapia + tecnicas de autocuidado e a combinacao mais eficaz.\n\n"
                "**Voce percorreu um longo caminho. Celebre esse passo.**"
            ),
            "content_type": "text",
            "duration_minutes": 8,
        },
    ])

    # ── Programs 3-5: seed minimal chapters (3 each as placeholder) ──────────
    # Full content can be expanded later without schema changes.
    op.bulk_insert(chapters_table, [
        # Autoestima e Confianca
        {
            "id": "autoestima-3-1", "program_id": "autoestima-confianca", "order": 1,
            "title": "Raizes da Autoestima",
            "content": "## Raizes da Autoestima\n\nA autoestima e construida ao longo da vida. Neste capitulo exploraremos como ela se forma e por que pode ser abalada.\n\n### De onde vem a autoestima\nA autoestima se desenvolve a partir de experiencias precoces, mensagens recebidas de figuras importantes e interpretacoes que fazemos de eventos de vida.\n\n### Reflexao\nPense em 3 mensagens que voce recebeu sobre si mesmo quando crianca. Como essas mensagens influenciam sua visao de si hoje?",
            "content_type": "text", "duration_minutes": 8,
        },
        {
            "id": "autoestima-3-2", "program_id": "autoestima-confianca", "order": 2,
            "title": "Critica Interna vs. Compaixao",
            "content": "## Critica Interna vs. Autocompaixao\n\nA voz critica interna e um dos maiores obstaculos para a autoestima saudavel.\n\n### Reconhecendo a critica interna\nNote os momentos em que voce se critica. Que palavras usa? Voce diria isso a um amigo?\n\n### Autocompaixao nao e fraqueza\nAutocompaixao e tratar a si mesmo com a mesma gentileza que ofereceria a alguem que voce ama. Pesquisas mostram que pessoas autocompassivas sao mais resilientes, nao menos.\n\n### Exercicio\nEscreva no diario algo que voce se critica. Agora reescreva como diria a um amigo proximo.",
            "content_type": "text", "duration_minutes": 9,
        },
        {
            "id": "autoestima-3-3", "program_id": "autoestima-confianca", "order": 3,
            "title": "Seus Valores como Bussola",
            "content": "## Seus Valores como Bussola\n\nViver alinhado aos proprios valores e um fundamento da autoestima autentica.\n\n### Identificando seus valores\nDe uma lista mental de qualidades: honestidade, criatividade, conexao, crescimento, coragem, cuidado, liberdade... Quais ressoam mais profundamente?\n\n### Valores vs. Regras sociais\nMuitas vezes seguimos regras que nao sao nossas. Distinguir o que e genuinamente seu do que e expectativa externa e um ato de autoconhecimento profundo.\n\n### Desafio\nAnote seus 5 valores principais. Em quais voce esta vivendo alinhado? Em quais ha discrepancia?",
            "content_type": "text", "duration_minutes": 10,
        },
        # Relacionamentos Saudaveis
        {
            "id": "relacionamentos-4-1", "program_id": "relacionamentos-saudaveis", "order": 1,
            "title": "Estilos de Apego",
            "content": "## Estilos de Apego\n\nNosso estilo de se relacionar foi moldado na infancia. Conhece-lo e o primeiro passo para relacoes mais saudaveis.\n\n### Os 4 estilos\n- **Seguro:** confortavel com intimidade e autonomia\n- **Ansioso:** teme abandono, busca validacao constante\n- **Evitativo:** evita proximidade, valoriza independencia em excesso\n- **Desorganizado:** oscila entre buscar e evitar conexao\n\n### Reflexao\nComo voce costuma reagir quando sente que alguem que voce ama pode se distanciar?",
            "content_type": "text", "duration_minutes": 9,
        },
        {
            "id": "relacionamentos-4-2", "program_id": "relacionamentos-saudaveis", "order": 2,
            "title": "Comunicacao Nao-Violenta",
            "content": "## Comunicacao Nao-Violenta (CNV)\n\nDesenvolvida por Marshall Rosenberg, a CNV transforma como nos expressamos e ouvimos.\n\n### Os 4 componentes\n1. **Observacao:** O que observo (sem julgamento)\n2. **Sentimento:** Como me sinto\n3. **Necessidade:** O que preciso\n4. **Pedido:** O que peco (especifico, realizavel)\n\n### Exemplo\n'Quando voce chega tarde sem avisar (observacao), eu me sinto ansiosa (sentimento) porque preciso de previsibilidade (necessidade). Voce poderia me mandar uma mensagem quando isso acontecer? (pedido)'\n\n### Pratica\nEscolha uma situacao recente e reformule usando os 4 componentes.",
            "content_type": "text", "duration_minutes": 10,
        },
        {
            "id": "relacionamentos-4-3", "program_id": "relacionamentos-saudaveis", "order": 3,
            "title": "Limites Saudaveis",
            "content": "## Limites Saudaveis\n\nLimites nao sao muros — sao a definicao de onde eu termino e o outro comeca.\n\n### Por que e dificil estabelecer limites\n- Medo de rejeicao ou conflito\n- Crenca de que e egoismo\n- Nao saber o que realmente queremos\n\n### Tipos de limites\n- **Fisicos:** toque, espaco pessoal\n- **Emocionais:** o que estou disposto a ouvir/absorver\n- **De tempo:** minha disponibilidade\n- **De valores:** o que nao estou disposto a fazer\n\n### Como estabelecer\n'Eu preciso...' / 'Nao estou confortavel com...' / 'Prefiro que...'\n\nLimites saudaveis aumentam o respeito mutuo e a autenticidade nos relacionamentos.",
            "content_type": "text", "duration_minutes": 9,
        },
        # Sono Reparador
        {
            "id": "sono-5-1", "program_id": "sono-reparador", "order": 1,
            "title": "A Ciencia do Sono",
            "content": "## A Ciencia do Sono\n\nO sono nao e um estado passivo — e quando o cerebro consolida memorias, o corpo se regenera e o sistema imune se fortalece.\n\n### Ciclos de sono\nUm ciclo dura cerca de 90 minutos e passa por:\n- **N1/N2:** sono leve\n- **N3:** sono profundo (restaurador fisico)\n- **REM:** sonhos, processamento emocional, consolidacao de memoria\n\n### Quanto precisamos\nAdultos: 7-9 horas. Mas a qualidade importa tanto quanto a quantidade.\n\n### Reflexao\nComo esta a sua qualidade de sono atualmente? O que mais interfere?",
            "content_type": "text", "duration_minutes": 7,
        },
        {
            "id": "sono-5-2", "program_id": "sono-reparador", "order": 2,
            "title": "Higiene do Sono",
            "content": "## Higiene do Sono\n\nPequenos habitos fazem grande diferenca na qualidade do descanso.\n\n### Habitos que ajudam\n- **Horario regular:** dormir e acordar no mesmo horario, inclusive fins de semana\n- **Quarto frio e escuro:** temperatura ideal 18-20°C\n- **Sem telas 1h antes:** luz azul suprime melatonina\n- **Rotina de desaceleracao:** leitura, banho quente, alongamento leve\n\n### Habitos que atrapalham\n- Cafeina apos 14h\n- Alcool (fragmenta os ciclos)\n- Exercicio intenso a noite\n- Trabalhar na cama\n\n### Desafio\nEscolha 2 habitos para implementar esta semana.",
            "content_type": "text", "duration_minutes": 8,
        },
        {
            "id": "sono-5-3", "program_id": "sono-reparador", "order": 3,
            "title": "Relaxamento Muscular Progressivo",
            "content": "## Relaxamento Muscular Progressivo\n\nTecnica desenvolvida pelo medico Edmund Jacobson, eficaz para reduzir tensao fisica antes de dormir.\n\n### Como praticar\nDeite-se. Comece pelos pes:\n1. **Tensione** o grupo muscular por 5 segundos\n2. **Solte** abruptamente e note a sensacao por 30 segundos\n3. Avance para o proximo grupo\n\n### Sequencia\nPes → panturrilhas → coxas → abdomen → maos → bracos → ombros → rosto\n\n### Beneficios\n- Reduz tempo para adormecer\n- Aumenta sono profundo\n- Diminui ansiedade noturna\n\nFaca esse exercicio como parte da sua rotina de desaceleracao.",
            "content_type": "text", "duration_minutes": 10,
        },
    ])


def downgrade() -> None:
    op.drop_table("chapters")
    op.drop_table("programs")
