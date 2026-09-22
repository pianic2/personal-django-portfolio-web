"""Generated snapshot of the PDPW-13 backend-owned canonical source subset."""

# Canonical editorial strings intentionally remain unwrapped to preserve the source snapshot.
# ruff: noqa: E501

import json

CANONICAL = json.loads(r'''{
  "shared": {
    "publicEvidence": [
      {
        "id": "portfolio-repository",
        "type": "repository",
        "url": "https://github.com/pianic2/its-react-portfolio-web"
      },
      {
        "id": "portfolio-quality-workflow",
        "type": "test",
        "url": "https://github.com/pianic2/its-react-portfolio-web/blob/main/.github/workflows/quality.yml"
      },
      {
        "id": "portfolio-content-model",
        "type": "documentation",
        "url": "https://github.com/pianic2/its-react-portfolio-web/blob/main/docs/content/irpw-9-content-model.md"
      },
      {
        "id": "portfolio-pages-documentation",
        "type": "documentation",
        "url": "https://github.com/pianic2/its-react-portfolio-web/blob/main/docs/deployment/github-pages.md"
      },
      {
        "id": "homeedge-repository",
        "type": "repository",
        "url": "https://github.com/pianic2/homeedge-ai-platform"
      },
      {
        "id": "homeedge-readme",
        "type": "documentation",
        "url": "https://github.com/pianic2/homeedge-ai-platform/blob/main/README.md"
      },
      {
        "id": "homeedge-product-vision",
        "type": "documentation",
        "url": "https://github.com/pianic2/homeedge-ai-platform/blob/main/docs/product/product-vision.md"
      },
      {
        "id": "laravel-repository",
        "type": "repository",
        "url": "https://github.com/pianic2/its-php-libreria"
      },
      {
        "id": "laravel-readme",
        "type": "documentation",
        "url": "https://github.com/pianic2/its-php-libreria/blob/main/README.md"
      },
      {
        "id": "node-repository",
        "type": "repository",
        "url": "https://github.com/pianic2/todo-list-manager-node"
      },
      {
        "id": "node-server-source",
        "type": "repository",
        "url": "https://github.com/pianic2/todo-list-manager-node/blob/main/src/server.js"
      },
      {
        "id": "node-ci-workflow",
        "type": "test",
        "url": "https://github.com/pianic2/todo-list-manager-node/blob/main/.github/workflows/ci.yml"
      }
    ],
    "capabilities": [
      {
        "id": "embedded-firmware",
        "category": "embedded"
      },
      {
        "id": "privacy-aware-design",
        "category": "security"
      },
      {
        "id": "technical-governance",
        "category": "architecture"
      },
      {
        "id": "laravel-api",
        "category": "backend"
      },
      {
        "id": "sanctum-authentication",
        "category": "security"
      },
      {
        "id": "containerized-delivery",
        "category": "delivery"
      },
      {
        "id": "node-api",
        "category": "backend"
      },
      {
        "id": "sqlite-persistence",
        "category": "backend"
      },
      {
        "id": "automated-testing",
        "category": "quality"
      }
    ],
    "projects": [
      {
        "id": "homeedge-ai-platform",
        "capabilityIds": [
          "embedded-firmware",
          "privacy-aware-design",
          "technical-governance"
        ],
        "evidence": [
          {
            "id": "homeedge-mvp-scope",
            "type": "documentation",
            "url": "https://github.com/pianic2/homeedge-ai-platform/blob/main/README.md"
          },
          {
            "id": "homeedge-architecture-governance",
            "type": "documentation",
            "url": "https://github.com/pianic2/homeedge-ai-platform/blob/main/README.md"
          },
          {
            "id": "homeedge-product-vision",
            "type": "documentation",
            "url": "https://github.com/pianic2/homeedge-ai-platform/blob/main/docs/product/product-vision.md"
          },
          {
            "id": "homeedge-stakeholder-review",
            "type": "report",
            "url": "https://niccolopiazzi01.atlassian.net/wiki/spaces/IEHAP/overview"
          }
        ],
        "links": [
          {
            "id": "homeedge-github",
            "kind": "repository",
            "url": "https://github.com/pianic2/homeedge-ai-platform"
          }
        ],
        "assetIds": [],
        "featured": true,
        "order": 0,
        "origin": "personal-long-term",
        "visualVariant": "signal-yellow"
      },
      {
        "id": "its-library-api-laravel",
        "capabilityIds": [
          "laravel-api",
          "sanctum-authentication",
          "containerized-delivery"
        ],
        "evidence": [
          {
            "id": "library-rest-endpoints",
            "type": "documentation",
            "url": "https://github.com/pianic2/its-php-libreria/blob/main/README.md"
          },
          {
            "id": "library-docker-setup",
            "type": "documentation",
            "url": "https://github.com/pianic2/its-php-libreria/blob/main/README.md"
          },
          {
            "id": "library-validation-tests",
            "type": "documentation",
            "url": "https://github.com/pianic2/its-php-libreria/blob/main/README.md"
          }
        ],
        "links": [
          {
            "id": "library-github",
            "kind": "repository",
            "url": "https://github.com/pianic2/its-php-libreria"
          }
        ],
        "assetIds": [],
        "featured": true,
        "order": 1,
        "origin": "its-training",
        "visualVariant": "studio-pink"
      },
      {
        "id": "node-list-manager",
        "capabilityIds": [
          "node-api",
          "sqlite-persistence",
          "automated-testing"
        ],
        "evidence": [
          {
            "id": "node-server-source",
            "type": "repository",
            "url": "https://github.com/pianic2/todo-list-manager-node/blob/main/src/server.js"
          },
          {
            "id": "node-package-manifest",
            "type": "documentation",
            "url": "https://github.com/pianic2/todo-list-manager-node/blob/main/README.md"
          },
          {
            "id": "node-automated-tests",
            "type": "test",
            "url": "https://github.com/pianic2/todo-list-manager-node/blob/main/.github/workflows/ci.yml"
          }
        ],
        "links": [
          {
            "id": "node-github",
            "kind": "repository",
            "url": "https://github.com/pianic2/todo-list-manager-node"
          }
        ],
        "assetIds": [],
        "featured": true,
        "order": 2,
        "origin": "its-training",
        "visualVariant": "electric-cyan"
      }
    ],
    "assets": []
  },
  "locales": {
    "it": {
      "profilePage": {
        "hero": {
          "eyebrow": "PROFILO",
          "title": "Ho trovato nell’informatica il modo di trasformare curiosità e logica in qualcosa di concreto.",
          "description": "Il mio percorso non è iniziato da una linea retta, ma da una domanda ricorrente: come funzionano davvero le cose? Oggi porto quella curiosità nello sviluppo software, costruendo progetti e competenze con metodo, trasparenza e continuità."
        },
        "sections": [
          {
            "id": "profile-vocation",
            "number": "01",
            "eyebrow": "VOCAZIONE",
            "title": "Prima del codice c’era il bisogno di capire.",
            "paragraphs": [
              "Mi hanno sempre attirato i problemi che richiedono ragionamento, pazienza e la capacità di collegare elementi diversi. Nell’informatica ho riconosciuto un ambiente in cui questa inclinazione poteva diventare operativa: non limitarsi a comprendere un sistema, ma provare a costruirne uno.",
              "Programmare mi permette di passare da un’idea astratta a un risultato osservabile. Ogni interfaccia, API o automazione diventa un modo per verificare una scelta, correggerla e imparare qualcosa di nuovo."
            ],
            "highlights": [
              "Curiosità per i sistemi",
              "Logica applicata",
              "Idee trasformate in software"
            ]
          },
          {
            "id": "profile-self-taught",
            "number": "02",
            "eyebrow": "FORMAZIONE AUTODIDATTA",
            "title": "Ho iniziato con ciò che avevo: tempo limitato, risorse online e molta pratica.",
            "paragraphs": [
              "Durante gli studi universitari e mentre lavoravo ho iniziato a formarmi da autodidatta. Ho seguito documentazione, corsi e guide, ma soprattutto ho cercato di trasformare ogni concetto in un esercizio o in un piccolo progetto che mi costringesse a confrontarmi con problemi reali.",
              "È stata una fase umile e disordinata, ma fondamentale. Mi ha insegnato a cercare informazioni, riconoscere ciò che non capivo, procedere per tentativi controllati e non aspettare condizioni perfette per iniziare."
            ],
            "highlights": [
              "Studio autonomo",
              "Università e lavoro",
              "Apprendimento attraverso la pratica"
            ]
          },
          {
            "id": "profile-its",
            "number": "03",
            "eyebrow": "ITS PRODIGI",
            "title": "Oggi sto trasformando l’apprendimento individuale in una preparazione professionale.",
            "paragraphs": [
              "Il percorso Full Stack Developer presso ITS Prodigi mi sta dando una struttura più solida. Lavoro su frontend, backend, database, testing e delivery, confrontandomi con vincoli, scadenze, revisioni e progetti che richiedono continuità.",
              "Sto imparando anche a rendere il lavoro comprensibile agli altri: organizzare il backlog, documentare le decisioni, raccogliere evidenze e distinguere chiaramente ciò che è già realizzato da ciò che è ancora pianificato."
            ],
            "highlights": [
              "Formazione Full Stack",
              "Progetti strutturati",
              "Collaborazione e tracciabilità"
            ]
          }
        ],
        "highlightsLabel": "Punti chiave",
        "usefulLinks": {
          "eyebrow": "LINK UTILI",
          "title": "Altri luoghi in cui puoi seguire il mio percorso.",
          "description": "Profili esterni ed evidenze che completano il portfolio. Questa raccolta crescerà insieme alle piattaforme su cui studio, pubblico e metto alla prova le mie competenze.",
          "items": [
            {
              "id": "leetcode",
              "label": "LeetCode",
              "description": "Il profilo dove raccolgo la pratica su algoritmi, strutture dati e problem solving.",
              "url": "https://leetcode.com/u/pianic2",
              "ctaLabel": "Apri il profilo LeetCode"
            }
          ]
        },
        "ctas": {
          "projectsLabel": "Apri LeetCode",
          "contactLabel": "Contattami",
          "githubLabel": "Esplora GitHub"
        },
        "closing": {
          "title": "Cerco contesti in cui continuare a crescere contribuendo davvero.",
          "description": "Sono aperto a stage curricolari, opportunità junior, piccoli progetti ben delimitati e collaborazioni formative. Se pensi che il mio percorso possa essere utile al tuo contesto, raccontami il problema e gli obiettivi."
        }
      },
      "projects": [
        {
          "projectId": "homeedge-ai-platform",
          "slug": "homeedge-ai-platform",
          "title": "HomeEdge AI Platform",
          "eyebrow": "SMART HOME · SISTEMI EMBEDDED",
          "detailEyebrow": "SMART HOME · EDGE COMPUTING · GOVERNANCE",
          "ctaLabel": "Scopri HomeEdge",
          "question": "Come raccogliere informazioni utili da una stanza senza rendere la casa un sistema poco trasparente?",
          "supportingText": "Il progetto è ancora nelle prime fasi, ma non è pensato come un esercizio isolato: voglio continuare a svilupparlo aggiungendo backend, applicazione mobile e nuove funzionalità solo dopo averne verificato i confini.",
          "whatIWorkedOn": "Ho definito la visione, i confini dell’MVP, la struttura del repository, la governance tecnica e il percorso di validazione dei componenti hardware.",
          "futureImprovement": "Il prossimo obiettivo è trasformare le decisioni e i test hardware in un nodo funzionante e collegarlo progressivamente a un backend e a un’applicazione mobile.",
          "originDescription": "HomeEdge non è un esercizio didattico isolato. È il progetto con cui approfondisco nel tempo sistemi embedded, architettura di prodotto e governance tecnica responsabile.",
          "narrative": {
            "cardSummary": "HomeEdge parte da piccoli nodi ESP32-C3 che rilevano temperatura, umidità, presenza locale e stato della porta.",
            "cardValue": "Unisce sensori fisici, architettura software e uso responsabile dei dati in un unico progetto.",
            "heroSummary": "HomeEdge è una piattaforma smart home sperimentale costruita intorno a piccoli sensori per le stanze. Il suo obiettivo è raccogliere informazioni utili vicino al luogo in cui vengono generate, senza trasformare la casa in un sistema opaco.",
            "idea": "Molti prodotti smart home non spiegano chiaramente quali dati raccolgono, dove vengono inviati o come il sistema prende le proprie decisioni. HomeEdge sperimenta un approccio più trasparente: ogni dispositivo ha uno scopo limitato, ogni tipo di dato ha un confine esplicito e ogni scelta importante viene documentata.",
            "built": "L’MVP attuale è concentrato su un nodo per stanza e porta basato su ESP32-C3. Misura temperatura e umidità, rileva localmente una presenza non identificativa e comunica se una porta è aperta o chiusa. Il repository definisce inoltre l’architettura, i rischi e le regole di lavoro che guideranno le fasi successive.",
            "value": "Il progetto combina programmazione embedded, architettura software, progettazione di un prodotto mobile e governance tecnica responsabile. Il suo valore non è soltanto nel nodo sensore: mostra anche come far crescere un sistema connesso senza nasconderne i limiti.",
            "currentStage": "HomeEdge si trova nella fase iniziale di sviluppo. Il nodo ESP32-C3 e i confini dell’MVP sono documentati. I servizi backend, l’applicazione mobile e le funzionalità assistite dall’AI sono direzioni pianificate che non sono ancora state dimostrate.",
            "evidenceIntroduction": "Il repository pubblico permette di controllare i confini dell’MVP, i segnali inclusi, la direzione architetturale e le regole usate per evitare affermazioni non supportate.",
            "transparency": "Il progetto viene gestito in modo trasparente attraverso GitHub, Jira e Confluence. GitHub contiene la fonte tecnica ufficiale, Jira traccia il lavoro pianificato e completato, mentre Confluence presenta agli stakeholder il contesto e i materiali di revisione."
          },
          "claims": [
            {
              "id": "sprint-zero-boundary",
              "text": "Il README documenta il confine del nodo MVP ESP32-C3 e i segnali inclusi.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-mvp-scope"
              ]
            },
            {
              "id": "target-services-unvalidated",
              "text": "Backend, applicazione mobile e funzionalità AI restano direzioni future, non funzionalità già completate.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-architecture-governance"
              ]
            },
            {
              "id": "product-vision-boundaries",
              "text": "La Product Vision spiega cosa intende diventare HomeEdge, quali funzionalità appartengono all’MVP attuale e quali idee restano fuori dal suo ambito presente.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-product-vision"
              ]
            },
            {
              "id": "project-progress-stakeholder-review",
              "text": "HomeEdge usa Jira per tracciare il lavoro e gli stati di revisione, mentre Confluence offre uno spazio rivolto agli stakeholder con contesto, report e materiali di verifica.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-stakeholder-review"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "homeedge-mvp-scope",
              "label": "Ambito dell’MVP e confini dei sensori",
              "description": "Il repository definisce quali segnali può raccogliere il primo nodo per stanza e porta e quali tipi di dati restano esclusi dall’MVP."
            },
            {
              "evidenceId": "homeedge-architecture-governance",
              "label": "Architettura e governance",
              "description": "La documentazione spiega come vengono revisionate le decisioni tecniche, i rischi e le funzionalità future prima di presentarle come lavoro completato."
            },
            {
              "evidenceId": "homeedge-product-vision",
              "label": "Visione del prodotto e confini dell’MVP",
              "description": "La Product Vision spiega cosa intende diventare HomeEdge, quali funzionalità appartengono all’MVP attuale e quali idee restano fuori dal suo ambito presente.",
              "linkLabel": "Leggi la Product Vision"
            },
            {
              "evidenceId": "homeedge-stakeholder-review",
              "label": "Avanzamento del progetto e stakeholder review",
              "description": "HomeEdge usa Jira per tracciare il lavoro e gli stati di revisione, mentre Confluence offre uno spazio rivolto agli stakeholder con contesto, report e materiali di verifica.",
              "linkLabel": "Apri lo spazio stakeholder di HomeEdge"
            }
          ],
          "links": [
            {
              "linkId": "homeedge-github",
              "label": "Repository GitHub"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "HomeEdge AI Platform",
            "description": "HomeEdge è una piattaforma smart home sperimentale costruita intorno a piccoli sensori per le stanze. Il suo obiettivo è raccogliere informazioni utili vicino al luogo in cui vengono generate, senza trasformare la casa in un sistema opaco.",
            "noIndex": false
          }
        },
        {
          "projectId": "its-library-api-laravel",
          "slug": "api-libreria-its-laravel",
          "title": "ITS Library API",
          "eyebrow": "LARAVEL · API REST",
          "detailEyebrow": "LARAVEL · API REST · LIBRERIA DIGITALE",
          "ctaLabel": "Scopri la Library API",
          "question": "Come organizzare libri, autori e categorie in un backend che sia semplice da provare e da mantenere?",
          "supportingText": "È il progetto in cui ho lavorato maggiormente sull’integrazione tra API, database, relazioni tra entità e protezione delle operazioni di modifica.",
          "whatIWorkedOn": "Ho lavorato sulla struttura delle API, sulle relazioni tra libri, autori e categorie, sull’autenticazione e sulla riproducibilità dell’ambiente Docker.",
          "futureImprovement": "Una possibile evoluzione è aggiungere un’interfaccia frontend e ampliare la gestione dei file e dei permessi.",
          "narrative": {
            "cardSummary": "Una API realizzata con Laravel per gestire una libreria digitale, con autenticazione tramite token, validazione dei dati, MySQL e supporto Docker.",
            "cardValue": "Mostra come autenticazione, validazione, relazioni tra dati e gestione dei file lavorano insieme in un backend reale.",
            "heroSummary": "ITS Library API è un backend didattico per gestire una collezione digitale di libri, autori e categorie attraverso endpoint chiari e documentati.",
            "idea": "Una libreria digitale richiede più di un elenco di titoli. Deve collegare i libri ai loro autori e alle categorie, validare le informazioni ricevute, proteggere le operazioni di modifica e offrire una configurazione che un altro sviluppatore possa riprodurre.",
            "built": "L’API permette la lettura pubblica e protegge le operazioni di scrittura tramite autenticazione. Gestisce libri, autori e categorie, usa Laravel Sanctum per gli accessi tramite token, salva i dati in MySQL e può associare file di testo scaricabili ai libri. Docker prepara localmente l’applicazione e il database.",
            "value": "Il progetto riunisce le parti essenziali di un vero backend: autenticazione, validazione, relazioni tra dati, archiviazione di file, errori prevedibili, documentazione e test automatici.",
            "currentStage": "Il repository documenta gli endpoint disponibili, gli esempi di richiesta, le regole di validazione, l’avvio locale e le credenziali dimostrative. È una API didattica pensata per essere riprodotta localmente, non un servizio commerciale di libreria già pubblicato online.",
            "evidenceIntroduction": "La documentazione pubblica mostra come avviare l’applicazione, ottenere un token di accesso, utilizzare gli endpoint disponibili e verificare il comportamento della validazione."
          },
          "claims": [
            {
              "id": "rest-resources",
              "text": "Il repository documenta risorse REST per libri, autori e categorie.",
              "status": "demonstrated",
              "evidenceIds": [
                "library-rest-endpoints"
              ]
            },
            {
              "id": "local-containers",
              "text": "Il setup locale documentato usa Docker Compose con Laravel e MySQL.",
              "status": "demonstrated",
              "evidenceIds": [
                "library-docker-setup",
                "library-validation-tests"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "library-rest-endpoints",
              "label": "Endpoint REST documentati",
              "description": "Il README elenca le operazioni pubbliche e protette per libri, autori, categorie e autenticazione."
            },
            {
              "evidenceId": "library-docker-setup",
              "label": "Configurazione Docker riproducibile",
              "description": "Docker Compose avvia l’applicazione Laravel, MySQL e l’interfaccia di amministrazione del database attraverso un processo di configurazione automatico."
            },
            {
              "evidenceId": "library-validation-tests",
              "label": "Validazione e test",
              "description": "Il progetto documenta le regole applicate ai dati ricevuti e include test automatici per i principali comportamenti del backend."
            }
          ],
          "links": [
            {
              "linkId": "library-github",
              "label": "Repository GitHub"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "ITS Library API",
            "description": "ITS Library API è un backend didattico per gestire una collezione digitale di libri, autori e categorie attraverso endpoint chiari e documentati.",
            "noIndex": false
          }
        },
        {
          "projectId": "node-list-manager",
          "slug": "gestore-liste-node",
          "title": "Progetto ITS Node.js",
          "eyebrow": "NODE.JS · EXPRESS · SQLITE",
          "detailEyebrow": "NODE.JS · EXPRESS · SQLITE",
          "ctaLabel": "Scopri il progetto Node.js",
          "question": "Quanto deve essere complesso un backend per gestire liste e attività?",
          "supportingText": "Qui l’obiettivo non era costruire una grande architettura, ma mantenere il codice leggibile e il progetto facile da verificare.",
          "whatIWorkedOn": "Ho organizzato le route, la persistenza SQLite e i test, cercando di mantenere il progetto piccolo e leggibile.",
          "futureImprovement": "Potrei estendere la validazione degli input e aggiungere un’interfaccia semplice per utilizzare il backend dal browser.",
          "narrative": {
            "cardSummary": "Un progetto compatto basato su Express e SQLite, con route separate e test automatici sui comportamenti principali.",
            "cardValue": "Mostra come mantenere una piccola applicazione ordinata, verificabile e facile da estendere senza introdurre complessità inutile.",
            "heroSummary": "Un backend compatto per gestire liste e attività, progettato per mantenere le route comprensibili, i dati persistenti e il comportamento facile da verificare.",
            "idea": "Anche una piccola applicazione per le attività può diventare difficile da mantenere quando route, persistenza e comportamento applicativo vengono mescolati. Questo progetto si concentra sulla separazione di queste responsabilità fin dall’inizio.",
            "built": "Il backend espone route Express modulari per liste e attività, salva i dati in SQLite e include test automatici per i principali comportamenti.",
            "value": "Il progetto è volutamente più piccolo di HomeEdge o della API Laravel. Il suo valore è mostrare come un backend focalizzato possa restare chiaro e verificabile senza aggiungere un’architettura che il problema non richiede.",
            "currentStage": "Il repository attuale dimostra il flusso del backend, l’organizzazione delle route, la persistenza SQLite e i test automatici. È un progetto didattico Node.js, non un servizio di gestione attività pronto per la produzione.",
            "evidenceIntroduction": "Il repository pubblico permette di controllare la struttura delle route, l’implementazione della persistenza e i test automatici."
          },
          "claims": [
            {
              "id": "express-route-modules",
              "text": "Il server Express monta moduli di route per liste e attività annidate.",
              "status": "demonstrated",
              "evidenceIds": [
                "node-server-source"
              ]
            },
            {
              "id": "sqlite-test-stack",
              "text": "Il manifest dichiara better-sqlite3, Jest e Supertest.",
              "status": "demonstrated",
              "evidenceIds": [
                "node-package-manifest",
                "node-automated-tests"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "node-server-source",
              "label": "Route Express modulari",
              "description": "Il backend separa gli endpoint utilizzati per gestire liste e attività in moduli dedicati."
            },
            {
              "evidenceId": "node-package-manifest",
              "label": "Persistenza SQLite",
              "description": "I dati dell’applicazione vengono salvati in un database SQLite locale e non scompaiono quando il server viene riavviato."
            },
            {
              "evidenceId": "node-automated-tests",
              "label": "Test automatici",
              "description": "La suite di test verifica il comportamento atteso delle principali operazioni del backend."
            }
          ],
          "links": [
            {
              "linkId": "node-github",
              "label": "Repository GitHub"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "Progetto ITS Node.js",
            "description": "Un backend compatto per gestire liste e attività, progettato per mantenere le route comprensibili, i dati persistenti e il comportamento facile da verificare.",
            "noIndex": false
          }
        }
      ]
    },
    "en": {
      "profilePage": {
        "hero": {
          "eyebrow": "PROFILE",
          "title": "I found in software the way to turn curiosity and logic into something concrete.",
          "description": "My path did not begin as a straight line, but with a recurring question: how do things really work? Today I bring that curiosity into software development, building projects and skills with method, transparency and continuity."
        },
        "sections": [
          {
            "id": "profile-vocation",
            "number": "01",
            "eyebrow": "VOCATION",
            "title": "Before the code, there was a need to understand.",
            "paragraphs": [
              "I have always been drawn to problems that require reasoning, patience and the ability to connect different elements. In software I found an environment where this inclination could become practical: not only understanding a system, but trying to build one.",
              "Programming lets me move from an abstract idea to an observable result. Every interface, API or automation becomes a way to test a decision, correct it and learn something new."
            ],
            "highlights": [
              "Curiosity about systems",
              "Applied logic",
              "Ideas turned into software"
            ]
          },
          {
            "id": "profile-self-taught",
            "number": "02",
            "eyebrow": "SELF-TAUGHT PHASE",
            "title": "I started with what I had: limited time, online resources and a lot of practice.",
            "paragraphs": [
              "While attending university and working, I began learning independently. I used documentation, courses and guides, but above all I tried to turn every concept into an exercise or small project that forced me to face real problems.",
              "It was a humble and sometimes untidy phase, but a fundamental one. It taught me how to search for information, identify what I did not understand, proceed through controlled attempts and start without waiting for perfect conditions."
            ],
            "highlights": [
              "Independent study",
              "University and work",
              "Learning through practice"
            ]
          },
          {
            "id": "profile-its",
            "number": "03",
            "eyebrow": "ITS PRODIGI",
            "title": "Today I am turning individual learning into professional preparation.",
            "paragraphs": [
              "The Full Stack Developer programme at ITS Prodigi is giving my path a stronger structure. I work across frontend, backend, databases, testing and delivery while dealing with constraints, deadlines, reviews and projects that require continuity.",
              "I am also learning to make the work understandable to others: organise a backlog, document decisions, collect evidence and distinguish clearly between what has already been delivered and what is still planned."
            ],
            "highlights": [
              "Full Stack training",
              "Structured projects",
              "Collaboration and traceability"
            ]
          }
        ],
        "highlightsLabel": "Key points",
        "usefulLinks": {
          "eyebrow": "USEFUL LINKS",
          "title": "Other places where you can follow my progress.",
          "description": "External profiles and evidence that complement this portfolio. This collection will grow with the platforms where I study, publish and test my skills.",
          "items": [
            {
              "id": "leetcode",
              "label": "LeetCode",
              "description": "The profile where I collect my practice with algorithms, data structures and problem solving.",
              "url": "https://leetcode.com/u/pianic2",
              "ctaLabel": "Open my LeetCode profile"
            }
          ]
        },
        "ctas": {
          "projectsLabel": "Open LeetCode",
          "contactLabel": "Contact me",
          "githubLabel": "Explore GitHub"
        },
        "closing": {
          "title": "I am looking for environments where I can keep growing while contributing real work.",
          "description": "I am open to curricular internships, junior opportunities, small well-scoped projects and educational collaborations. If you think my path could fit your context, tell me about the problem and the objectives."
        }
      },
      "projects": [
        {
          "projectId": "homeedge-ai-platform",
          "slug": "homeedge-ai-platform",
          "title": "HomeEdge AI Platform",
          "eyebrow": "SMART HOME · EMBEDDED SYSTEMS",
          "detailEyebrow": "SMART HOME · EDGE COMPUTING · GOVERNANCE",
          "ctaLabel": "Discover HomeEdge",
          "question": "How can a room provide useful information without turning the home into an opaque system?",
          "supportingText": "The project is still at an early stage, but it is not intended as a one-off experiment. I plan to keep developing it, adding backend and mobile capabilities only after their boundaries have been properly tested.",
          "whatIWorkedOn": "I defined the product vision, the MVP boundaries, the repository structure, the technical governance and the hardware validation path.",
          "futureImprovement": "The next goal is to turn the hardware decisions and tests into a working node and gradually connect it to a backend and a mobile application.",
          "originDescription": "HomeEdge is not a one-off course assignment. It is the project I use to explore embedded systems, product architecture and responsible technical governance over the long term.",
          "narrative": {
            "cardSummary": "HomeEdge starts with small ESP32-C3 nodes that measure temperature and humidity, detect local presence and report whether a door is open or closed.",
            "cardValue": "It brings together physical sensors, software architecture and responsible data use in one project.",
            "heroSummary": "HomeEdge is an experimental smart-home platform built around small room sensors. Its purpose is to collect useful information close to where it is generated, without turning the home into an opaque system.",
            "idea": "Many smart-home products do not clearly explain what they collect, where the information goes or how the system makes decisions. HomeEdge explores a more transparent approach: every device has a limited purpose, every type of data has an explicit boundary and every important choice is documented.",
            "built": "The current MVP focuses on an ESP32-C3 room and door node. It measures temperature and humidity, detects non-identifying presence locally and reports whether a door is open or closed. The repository also defines the architecture, risks and working rules that guide the next phases.",
            "value": "The project combines embedded programming, software architecture, mobile-product thinking and responsible technical governance. Its value is not only the sensor node: it also demonstrates how a connected system can grow without hiding its limitations.",
            "currentStage": "HomeEdge is currently in its initial development phase. The ESP32-C3 node and the MVP boundaries are documented. Backend services, the mobile application and AI-assisted insights are planned directions that have not been demonstrated yet.",
            "evidenceIntroduction": "The public repository allows visitors to inspect the MVP boundaries, the included sensor signals, the architectural direction and the rules used to prevent unsupported claims.",
            "transparency": "The project is managed transparently across GitHub, Jira and Confluence. GitHub contains the technical source of truth, Jira tracks planned and completed work, and Confluence presents project context and review material to stakeholders."
          },
          "claims": [
            {
              "id": "sprint-zero-boundary",
              "text": "The README documents the ESP32-C3 MVP node boundary and included signals.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-mvp-scope"
              ]
            },
            {
              "id": "target-services-unvalidated",
              "text": "Backend, mobile and AI capabilities remain future directions rather than completed features.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-architecture-governance"
              ]
            },
            {
              "id": "product-vision-boundaries",
              "text": "The Product Vision explains what HomeEdge is intended to become, which capabilities belong to the current MVP and which ideas remain outside its present scope.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-product-vision"
              ]
            },
            {
              "id": "project-progress-stakeholder-review",
              "text": "HomeEdge uses Jira to track work and review status, while Confluence provides a stakeholder-facing space for project context, reports and review material.",
              "status": "demonstrated",
              "evidenceIds": [
                "homeedge-stakeholder-review"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "homeedge-mvp-scope",
              "label": "MVP scope and sensor boundaries",
              "description": "The repository defines which signals the first room and door node can collect and which types of data remain outside the MVP."
            },
            {
              "evidenceId": "homeedge-architecture-governance",
              "label": "Architecture and governance",
              "description": "The documentation explains how technical decisions, risks and future capabilities are reviewed before being presented as completed work."
            },
            {
              "evidenceId": "homeedge-product-vision",
              "label": "Product vision and MVP boundaries",
              "description": "The Product Vision explains what HomeEdge is intended to become, which capabilities belong to the current MVP and which ideas remain outside its present scope.",
              "linkLabel": "Read the Product Vision"
            },
            {
              "evidenceId": "homeedge-stakeholder-review",
              "label": "Project progress and stakeholder review",
              "description": "HomeEdge uses Jira to track work and review status, while Confluence provides a stakeholder-facing space for project context, reports and review material.",
              "linkLabel": "Open the HomeEdge stakeholder space"
            }
          ],
          "links": [
            {
              "linkId": "homeedge-github",
              "label": "GitHub repository"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "HomeEdge AI Platform",
            "description": "HomeEdge is an experimental smart-home platform built around small room sensors. Its purpose is to collect useful information close to where it is generated, without turning the home into an opaque system.",
            "noIndex": false
          }
        },
        {
          "projectId": "its-library-api-laravel",
          "slug": "its-library-api-laravel",
          "title": "ITS Library API",
          "eyebrow": "LARAVEL · REST API",
          "detailEyebrow": "LARAVEL · REST API · DIGITAL LIBRARY",
          "ctaLabel": "Discover the Library API",
          "question": "How can books, authors and categories be organised in a backend that is easy to run and maintain?",
          "supportingText": "This project helped me work on the relationship between API design, database entities and protected write operations.",
          "whatIWorkedOn": "I worked on the API structure, the relationships between books, authors and categories, authentication and the reproducibility of the Docker environment.",
          "futureImprovement": "A possible next step would be adding a frontend interface and expanding file and permission management.",
          "narrative": {
            "cardSummary": "A Laravel API for managing a digital library, including token authentication, data validation, MySQL and Docker support.",
            "cardValue": "It shows how authentication, validation, data relationships and file management work together in a real backend.",
            "heroSummary": "ITS Library API is an educational backend for managing a digital collection of books, authors and categories through clear and documented endpoints.",
            "idea": "A digital library needs more than a list of titles. It must connect books with their authors and categories, validate incoming information, protect editing operations and provide a setup that another developer can reproduce.",
            "built": "The API supports public reading and authenticated write operations. It manages books, authors and categories, uses Laravel Sanctum for token-based access, stores data in MySQL and can associate downloadable text files with books. Docker prepares the application and its database locally.",
            "value": "This project brings together the essential parts of a real backend: authentication, validation, database relationships, file storage, predictable errors, documentation and automated tests.",
            "currentStage": "The repository documents the available endpoints, request examples, validation rules, local bootstrap and demo credentials. It is an educational API designed for local reproduction, not a hosted commercial library service.",
            "evidenceIntroduction": "The public documentation shows how to start the application, obtain an access token, use the available endpoints and verify the validation behaviour."
          },
          "claims": [
            {
              "id": "rest-resources",
              "text": "The repository documents REST resources for books, authors and categories.",
              "status": "demonstrated",
              "evidenceIds": [
                "library-rest-endpoints"
              ]
            },
            {
              "id": "local-containers",
              "text": "The documented local setup uses Docker Compose with Laravel and MySQL.",
              "status": "demonstrated",
              "evidenceIds": [
                "library-docker-setup",
                "library-validation-tests"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "library-rest-endpoints",
              "label": "Documented REST endpoints",
              "description": "The README lists public and protected operations for books, authors, categories and authentication."
            },
            {
              "evidenceId": "library-docker-setup",
              "label": "Reproducible Docker setup",
              "description": "Docker Compose starts the Laravel application, MySQL and the database administration interface with an automated bootstrap process."
            },
            {
              "evidenceId": "library-validation-tests",
              "label": "Validation and tests",
              "description": "The project documents its input rules and includes automated tests for important backend behaviour."
            }
          ],
          "links": [
            {
              "linkId": "library-github",
              "label": "GitHub repository"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "ITS Library API",
            "description": "ITS Library API is an educational backend for managing a digital collection of books, authors and categories through clear and documented endpoints.",
            "noIndex": false
          }
        },
        {
          "projectId": "node-list-manager",
          "slug": "node-list-manager",
          "title": "ITS Node.js Project",
          "eyebrow": "NODE.JS · EXPRESS · SQLITE",
          "detailEyebrow": "NODE.JS · EXPRESS · SQLITE",
          "ctaLabel": "Discover the Node.js project",
          "question": "How complex does a backend need to be to manage lists and tasks?",
          "supportingText": "The goal was not to create a large architecture, but to keep the code understandable and the project easy to verify.",
          "whatIWorkedOn": "I organised the routes, SQLite persistence and tests, keeping the project small and readable.",
          "futureImprovement": "I could extend input validation and add a simple browser interface for using the backend.",
          "narrative": {
            "cardSummary": "A compact Express and SQLite project with separated routes and automated tests for its main behaviour.",
            "cardValue": "It demonstrates how to keep a small application organised, testable and easy to extend without unnecessary complexity.",
            "heroSummary": "A compact backend for managing lists and tasks, designed to keep routes understandable, data persistent and behaviour easy to verify.",
            "idea": "Even a small task application can become difficult to maintain when routes, persistence and application behaviour are mixed together. This project focuses on separating those responsibilities from the beginning.",
            "built": "The backend exposes modular Express routes for lists and tasks, stores its data in SQLite and includes automated tests for the main behaviours.",
            "value": "The project is intentionally smaller than HomeEdge or the Laravel API. Its value is showing how a focused backend can remain clear and testable without adding architecture that the problem does not require.",
            "currentStage": "The current repository demonstrates the backend flow, the route organisation, SQLite persistence and automated testing. It is an educational Node.js project rather than a production task-management service.",
            "evidenceIntroduction": "The public repository makes it possible to inspect the route structure, the persistence implementation and the automated tests."
          },
          "claims": [
            {
              "id": "express-route-modules",
              "text": "The Express server mounts route modules for lists and nested items.",
              "status": "demonstrated",
              "evidenceIds": [
                "node-server-source"
              ]
            },
            {
              "id": "sqlite-test-stack",
              "text": "The manifest declares better-sqlite3, Jest and Supertest.",
              "status": "demonstrated",
              "evidenceIds": [
                "node-package-manifest",
                "node-automated-tests"
              ]
            }
          ],
          "evidence": [
            {
              "evidenceId": "node-server-source",
              "label": "Modular Express routes",
              "description": "The backend separates the endpoints used to manage lists and tasks into focused route modules."
            },
            {
              "evidenceId": "node-package-manifest",
              "label": "SQLite persistence",
              "description": "Application data is stored in a local SQLite database instead of disappearing when the server restarts."
            },
            {
              "evidenceId": "node-automated-tests",
              "label": "Automated tests",
              "description": "The test suite verifies the expected behaviour of the main backend operations."
            }
          ],
          "links": [
            {
              "linkId": "node-github",
              "label": "GitHub repository"
            }
          ],
          "assets": [],
          "metadata": {
            "title": "ITS Node.js Project",
            "description": "A compact backend for managing lists and tasks, designed to keep routes understandable, data persistent and behaviour easy to verify.",
            "noIndex": false
          }
        }
      ]
    }
  }
}''')
