import EvidenceDetails from './EvidenceDetails';

const STARTER_QUESTIONS = [
  'Give me an overview of Fenton Village',
  'What is the population of Fenton Village?',
  'How do people commute to work?',
  'How many restaurants are nearby?',
  'Which business could be successful opening here?',
];

function AskCommunity({ question, onQuestionChange, onAsk, status, result, error }) {
  const suggestions = result?.suggestions?.length ? result.suggestions : STARTER_QUESTIONS;
  const sources = (result?.evidence ?? []).map((item, index) => ({
    id: `query-evidence-${index}`,
    organization: item.organization,
    dataset: item.dataset,
    year: item.dataset_year ?? '',
    geography: 'Fenton Village study area',
    table: item.source_variable ?? '',
    url: item.source_url,
  }));

  return (
    <section className="ask-community" aria-labelledby="ask-community-title">
      <div className="ask-community-heading">
        <p className="eyebrow">Ask the community data</p>
        <h2 id="ask-community-title">What would you like to know about Fenton Village?</h2>
        <p>Ask about people, businesses, transportation, or community characteristics.</p>
      </div>
      <form className="ask-community-form" onSubmit={(event) => { event.preventDefault(); onAsk(); }}>
        <label className="visually-hidden" htmlFor="community-question">Ask a question</label>
        <input
          id="community-question"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="How do people commute to work?"
          maxLength={500}
        />
        <button className="primary-button" type="submit" disabled={!question.trim() || status === 'loading'}>
          {status === 'loading' ? 'Answering…' : 'Ask'}
        </button>
      </form>
      <div className="suggested-questions" aria-label="Suggested questions">
        {suggestions.slice(0, 4).map((suggestion) => (
          <button type="button" key={suggestion} onClick={() => onQuestionChange(suggestion)}>
            {suggestion}
          </button>
        ))}
      </div>
      {error && <p className="query-error" role="alert">The API did not answer this question. Confirm the backend is running and VITE_API_BASE_URL is configured.</p>}
      {result && (
        <article className="query-answer" aria-live="polite">
          <div>
            <span className="answer-label">Answer from stored public data</span>
            <p>{result.answer}</p>
          </div>
          {result.limitations?.length > 0 && (
            <details>
              <summary>Important limitations</summary>
              <ul>{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </details>
          )}
          <EvidenceDetails sources={sources} label="Verify this answer" />
        </article>
      )}
    </section>
  );
}

export default AskCommunity;
