# Fotos oficiais dos programas — Guia de estilo + prompts

Gere no Midjourney / DALL·E / Ideogram. Uma imagem por programa, salvar como
`programs/{slug}.jpg` no S3 e preencher `programs.cover_image_key`.

## Guia de estilo (colar como prefixo de TODOS os prompts)

> Warm editorial lifestyle photography, soft natural window light, calm and
> hopeful mood, Brazilian everyday realism, diverse Brazilian people, muted
> earthy palette with teal and lavender accents, shallow depth of field,
> no text, no logos, no clinical or hospital imagery, 16:10 aspect ratio —

Regras: nunca rostos em close com expressão de sofrimento explícito (tom
acolhedor, não dramático); nada de imagens "de estoque genérico" (aperto de mão,
cérebro 3D); pessoas reais em cenas reais.

## PILAR 1 — Mindfulness (tons: verde-sage, luz de manhã)

| slug | prompt (após o prefixo) |
|---|---|
| presenca-21-dias | woman breathing calmly by an open window at sunrise, eyes closed, plants nearby, morning tea steaming |
| respira-kit-sos | person pausing with hand on chest inside a parked car in city traffic, serene expression, soft light |
| mindfulness-no-trabalho | professional taking a mindful pause at a tidy desk, closed laptop, cup of coffee, office plants, calm posture |
| comer-com-presenca | hands savoring a simple colorful meal at a wooden table, no phone, natural light, unhurried |
| maternidade-presente | mother with baby sling breathing calmly on a sofa, morning chaos softly blurred in background, gentle smile |
| autocompaixao-na-pratica | person writing kindly in a journal wrapped in a soft blanket, warm lamp light, cozy corner |
| mindfulness-aprofundado | person in seated meditation on a cushion in a minimal sunlit room, straight dignified posture |
| retiro-online-um-dia | cozy home corner arranged for a day of silence: cushion, candle, journal, headphones, soft daylight |

## PILAR 2 — Ansiedade (tons: teal, luz suave)

| slug | prompt |
|---|---|
| ansiedade-sob-controle | person exhaling with relief on a balcony at golden hour, city softly out of focus, shoulders relaxing |
| primeiros-socorros-emocionais | close-up of grounded bare feet and a steady hand touching a textured wall, present-moment anchoring |
| diario-de-pensamentos | open structured journal with pen and tea on a desk, morning light, sense of order emerging |
| mente-sem-ruminacao | person closing a mental "loop": walking away lighter on a tree-lined street, loose hair in breeze |
| conversas-sem-panico | person speaking calmly in a small friendly group, warm café setting, confident relaxed body language |
| foco-na-prova | student at organized study desk taking a deep confident breath, exam materials neat, dawn light |
| trabalho-sem-sufoco | professional leaving the office at a humane hour, backpack on, relieved light expression, sunset |
| ansiedade-financeira | person calmly reviewing finances at kitchen table, coffee, honest serene expression, no drama |
| desconecta | phone face-down on a nightstand while person reads a paper book, warm lamp, peaceful evening |
| intensivo-ansiedade | supportive circle of diverse people in a bright living-room video call setup, warm connection |

## PILAR 3 — Autoestima (tons: terracota, luz dourada)

| slug | prompt |
|---|---|
| meu-valor | person smiling gently at their own reflection in a hallway mirror, morning light, self-acceptance |
| diario-do-meu-valor | hands writing in an elegant journal beside dried flowers, golden afternoon light |
| silenciando-a-critica-interna | person turning down the volume of an old radio, metaphorical calm, warm domestic scene |
| feito-e-melhor-que-perfeito | joyfully imperfect handmade ceramic mug held with pride, clay-stained hands, workshop light |
| sindrome-da-impostora | professional woman standing confident in her workspace, subtle proud smile, awards softly blurred |
| recomeco-pos-termino | person opening curtains to bright morning light in a room being reorganized, fresh start |
| espelho-amigo | person laughing naturally while taking a casual unposed photo, real skin, authentic joy |
| fale-por-voce | person speaking up at a table with calm assertive gesture, respectful listeners, balanced light |
| florescer-45 | radiant woman 50s planting flowers in a sunlit garden, confident and serene, rich golden light |

## PILAR 4 — Relacionamentos (tons: rosa-plum, luz quente)

| slug | prompt |
|---|---|
| falando-a-mesma-lingua | couple in genuine conversation on a sofa, turned toward each other, warm evening light, connection |
| fml-audio-planner | person walking in a park with earphones, gentle smile, listening attentively, morning light |
| fml-a-dois | couple doing a guided activity together at kitchen table with cards and notebook, laughing softly |
| fml-conversas-dificeis | couple holding hands across a table before an important conversation, brave and tender |
| baralho-fml | question cards spread on a picnic blanket between two people, playful intimate atmosphere |
| fml-turma-acompanhada | warm online group session grid on a laptop, diverse couples, sense of community |
| limites-sem-culpa | person gently but firmly gesturing "no" with a kind expression, doorway of their home, self-possessed |
| brigando-direito | couple in a calm repair moment after conflict, one offering tea, soft reconciliation light |
| reacender | long-married couple slow dancing in the kitchen at night, string lights, rekindled tenderness |
| depois-da-tempestade | couple rebuilding: planting a tree together in their backyard after rain, hopeful sky clearing |
| amor-sem-dependencia | person content alone with a book and coffee, full life visible, secure and serene |
| terminos-conscientes | two cups of tea and a heartfelt letter on a table, dignified farewell, gentle light |
| mesma-lingua-em-casa | parent and teenager side by side on a bench, relaxed real conversation, late afternoon |
| sogros-cunhados-afins | multigenerational Sunday lunch table with light laughter, warm Brazilian family scene |
| mesma-lingua-no-trabalho | two colleagues in respectful honest conversation by a window, coffee cups, professional warmth |

## PILAR 5 — Sono (tons: índigo/plum, luz noturna suave)

| slug | prompt |
|---|---|
| reaprendendo-a-dormir | inviting bedroom at dusk: neat bed, dim warm lamp, journal on nightstand, deep calm |
| kit-noite-boa | nightstand ritual: herbal tea, sleep journal, soft lamp, phone away, peaceful order |
| mente-silenciosa-21-noites | person writing thoughts into a journal in bed before sleep, mind visibly unburdening, cozy dark |
| audios-para-dormir | person with soft headphones drifting to sleep, serene face barely lit by moonlight |
| desliga-telas-e-sono | phone charging far from the bed while person sleeps peacefully, blue-free warm darkness |
| sono-de-plantao | nurse sleeping deeply during daytime with quality blackout curtains, protected rest, respect |
| noites-em-familia | tired but tender parents tag-teaming at night nursery, realistic warm scene, mutual care |
| dormir-bem-acompanhado | small online group reviewing sleep diaries together, supportive evening session, warm screens |

## Depois de gerar

1. Upload para S3: `s3://{bucket}/programs/{slug}.jpg` (≤ 400KB, 1600×1000)
2. `UPDATE programs SET cover_image_key = 'programs/{slug}.jpg' WHERE slug = '{slug}';`
3. O app usa `expo-image` com o gradiente da categoria como fallback/placeholder
