---
layout: default
---

<section class="intro">
  <h1>Diagnosis</h1>
  <p class="tagline">Explains why an execution trace violates a temporal requirement.</p>
  <p>
    A trace checker reports that a requirement is violated, not why. Diagnosis checks
    many small variations of the violated requirement against the trace and learns a
    decision tree from the results. The tree shows which thresholds, time bounds, and
    connectives of the requirement are involved in the violation.
  </p>
  <p class="links">
    <a href="{{ site.repository_url }}">GitHub repository</a>
    <a href="#get-started">Get started</a>
  </p>
</section>

<section id="scenario">
  <h2>Illustrative scenario</h2>
  <p>
    An <em>ego</em> vehicle drives next to a <em>target</em> vehicle that cuts into its
    lane. Requirement φ<sub>3</sub> asks the ego vehicle to react: when the target is in
    the central portion of the lane (0.5&nbsp;m &lt; <i>y</i><sub>pos</sub> &lt; 3.5&nbsp;m)
    and close to the ego vehicle (<i>x</i><sub>gap</sub> &lt; 2.0&nbsp;m and
    <i>y</i><sub>gap</sub> &lt; 1.5&nbsp;m), the lateral gap must grow above 1.0&nbsp;m
    within one second.
  </p>
  <figure class="scenario">
    <img src="{{ '/assets/media/retry-scenario.png' | relative_url }}" width="2800" height="1680"
      alt="Two-lane road. The target vehicle has aborted a first cut-in and is cutting in a second time. At 5.2 s its lateral position y_pos is 2.8 m, the lateral gap y_gap to the ego vehicle is 1.2 m, and the longitudinal gap x_gap is 0.85 m.">
    <figcaption>
      The retry scenario at 5.2&nbsp;s. The target aborted a first cut-in and is cutting in
      again. The shaded band is the central portion of the lane.
    </figcaption>
  </figure>
  <p>
    At 5.2&nbsp;s all conditions of φ<sub>3</sub> hold, but the lateral gap keeps
    shrinking instead of growing above 1.0&nbsp;m, so the trace violates φ<sub>3</sub>.
  </p>
</section>

<section id="how-it-works">
  <h2>How it works</h2>
  <figure class="wide">
    <video autoplay muted loop playsinline preload="auto" width="1400" height="560"
      poster="{{ '/assets/media/method-pipeline-poster.svg' | relative_url }}"
      aria-label="Animation of three generations of the search on requirement φ3 of the scenario: mutants are sampled, checked against the trace, and the decision tree is relearned from the verdicts.">
      <source src="{{ '/assets/media/method-pipeline.mp4' | relative_url }}" type="video/mp4">
    </video>
  </figure>
  <ol class="steps">
    <li>
      <strong>Mutate.</strong> Generate variants of the requirement within a mutation
      space you define: which elements may change, and to which values.
    </li>
    <li>
      <strong>Check.</strong> Check each variant against the trace. The trace checker
      is used as a black box and can be replaced.
    </li>
    <li>
      <strong>Explain.</strong> Learn a decision tree from the verdicts. Its splits show
      which elements separate satisfied from violated variants.
    </li>
  </ol>
  <p>
    The search repeats these steps until the tree stabilizes or the time budget runs out.
  </p>
</section>

<section id="result">
  <h2>Result</h2>
  <p>
    On the retry trace, the tree points to the time window after about 5.2&nbsp;s and a
    lateral position above about 2.8&nbsp;m. Inspecting the controller over that window
    revealed a flag that was not reset when the target cut in a second time.
  </p>
  <figure class="tree">
    <img src="{{ '/assets/media/decision-tree.svg' | relative_url }}" width="696" height="486"
      alt="Decision tree learned for requirement φ3. The root splits on the end of the time window at 4.6998 s; along the and branch, the tree splits on the window at 5.2003 s and on the lateral-position bound at 2.8006 m.">
  </figure>
</section>

<section id="get-started">
  <h2>Get started</h2>
  <p>
    Diagnosis runs in Docker. Requirements are written in the Hybrid Logic of Signals
    (HLS) and traces are encoded as Z3 constraints.
  </p>
<pre><code>git clone https://github.com/rdinizcal/Diagnosis
cd Diagnosis/docker
docker compose build
docker compose run --rm diagnosis run --config configs/AT1_config_exp1.json</code></pre>
  <p>
    A configuration file defines the mutation space. In this one, position 2 of the
    requirement can switch between <em>and</em> and <em>or</em>, position 6 between
    <code>&lt;</code> and <code>&gt;</code>, and the speed threshold at position 11 can
    take values between 100 and 140:
  </p>
<pre><code>"mutation": {
  "max_mutations": 1,
  "allowed_positions": [2, 6, 11],
  "allowed_changes": {
    "2":  { "logical":    ["And", "Or"] },
    "6":  { "relational": ["&lt;", "&gt;"] },
    "11": { "numeric":    [100.0, 140.0] }
  }
}</code></pre>
  <p>
    See the repository's <a href="{{ site.repository_url }}#readme">README</a> for the
    full set of options.
  </p>
</section>

<section id="paper">
  <h2>Paper</h2>
  <p>
    <em>Search-based Trace Diagnostic for Cyber-Physical Systems.</em>
    R. Caldas, G. Araujo, F. Formica, G. Rodrigues, P. Pelliccione, C. Menghi.
    Under review at IEEE Transactions on Software Engineering.
  </p>
  <p>
    In 34 experiments on automotive and robotics requirements, Diagnosis produced a
    diagnosis consistent with an expert's in 29.
  </p>
  <p class="links">
    <a href="{{ site.replication_url }}">Replication package</a>
    <a href="mailto:ricardo.caldas@gssi.it">Contact: ricardo.caldas@gssi.it</a>
  </p>
  <details>
    <summary>BibTeX</summary>
<pre><code>@unpublished{diagnosis-sbtd,
  title  = {Search-based Trace Diagnostic for Cyber-Physical Systems},
  author = {Caldas, Ricardo and Araujo, Gabriel and Formica, Federico and
            Rodrigues, Genaína and Pelliccione, Patrizio and Menghi, Claudio},
  year   = {2026},
  note   = {Manuscript under review at IEEE Transactions on Software Engineering}
}</code></pre>
  </details>
</section>
