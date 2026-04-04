export default function Home() {
  const pillars = [
    {
      title: "Biometrie iris multi-couche",
      description:
        "Capture guidee, controle qualite et reconnaissance robuste pour limiter les erreurs et les usurpations.",
    },
    {
      title: "Protection anti-spoofing",
      description:
        "Analyse de vivacite et verification de coherence visuelle pour detecter les attaques par image ou video.",
    },
    {
      title: "Securite orientee wallet",
      description:
        "Architecture orientee protection des identites et des transactions, avec une couche crypto dediee.",
    },
  ];

  const roadmap = [
    "Acquisition et normalisation de l'iris",
    "Extraction et comparaison des empreintes",
    "Validation anti-spoofing et decision",
    "Integration dans le parcours wallet",
  ];

  return (
    <main className="vitrine">
      <section className="hero section-pad">
        <div className="hero-copy fade-up">
          <p className="eyebrow">REAL ETH 2026</p>
          <h1>
            Le wallet nouvelle generation
            <span> securise par reconnaissance de l&apos;iris.</span>
          </h1>
          <p className="lead">
            Nous construisons une experience d&apos;authentification fluide qui combine
            IA, biometrie et securite crypto pour rendre l&apos;acces aux actifs
            numeriques plus sur et plus simple.
          </p>
          <div className="actions">
            <a href="#vision" className="btn btn-primary">
              Decouvrir le projet
            </a>
            <a href="#contact" className="btn btn-ghost">
              Nous contacter
            </a>
          </div>
        </div>
        <div className="hero-panel fade-up">
          <p>Mission</p>
          <strong>
            Supprimer la friction d&apos;acces tout en augmentant fortement la
            confiance sur chaque transaction.
          </strong>
          <ul>
            <li>Hardware de capture dedie</li>
            <li>API de verification modulaire</li>
            <li>Pipeline de reconnaissance explicable</li>
          </ul>
        </div>
      </section>

      <section id="vision" className="section-pad">
        <div className="section-head fade-up">
          <p className="eyebrow">Vision Produit</p>
          <h2>Un socle de confiance pour l&apos;identite numerique.</h2>
        </div>
        <div className="pillars">
          {pillars.map((pillar) => (
            <article key={pillar.title} className="card fade-up">
              <h3>{pillar.title}</h3>
              <p>{pillar.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-pad process-wrap">
        <div className="process fade-up">
          <p className="eyebrow">Comment ca marche</p>
          <h2>Du scan iris a l&apos;acces wallet en quatre etapes.</h2>
          <ol>
            {roadmap.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      </section>

      <section id="contact" className="section-pad">
        <div className="cta fade-up">
          <h2>Vous voulez collaborer avec l&apos;equipe RealETH 2026 ?</h2>
          <p>
            Nous sommes ouverts aux partenariats techniques, tests terrain et
            discussions avec investisseurs ou incubateurs.
          </p>
          <a className="btn btn-primary" href="mailto:contact@realeth2026.io">
            contact@realeth2026.io
          </a>
        </div>
      </section>
    </main>
  );
}
