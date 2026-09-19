import EvidenceDetails from './EvidenceDetails';

const STARTER_QUESTIONS = [
  'Give me an overview of Fenton Village',
  'What is the population of Fenton Village?',
  'How do people commute to work?',
  'How many restaurants are nearby?',
  'Which business could be successful opening here?',
];

function AskCommunity({ question, onQuestionChange, onAsk, status, result, error, areaName, isAreaSelected }) {
  const suggestions = isAreaSelected
    ? ['Give me an overview of this tract', 'What is the population?', 'What is the median household income?', 'How do people commute to work?']
    : result?.suggestions?.length ? result.suggestions : STARTER_QUESTIONS;
  const sources = (result?.evidence ?? []).map((item, index) => ({
    id: `query-evidence-${index}`,
    organization: item.organization,
    dataset: item.dataset,
    year: item.dataset_year ?? '',
    geography: item.geography || areaName,
    table: item.source_variable ?? '',
    url: item.source_url,
  }));

  return (
    <section className="ask-community" aria-labelledby="ask-community-title">
      <div className="ask-community-heading">
        <p className="eyebrow">Ask the community data</p>
        <h2 id="ask-community-title">What would you like to know?</h2>
        <p>Ask about people, businesses, transportation, or community characteristics.</p>
      </div>
      <p className="query-context" aria-live="polite"><span>Asking about</span><strong>{areaName}</strong></p>
      <form className="ask-community-form" onSubmit={(event) => { event.preventDefault(); onAsk(); }}>
        <label className="visually-hidden" htmlFor="community-question">Ask a question</label>
        <input
          id="community-question"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Ask about this community..."
          maxLength={500}
        />
        <button className="primary-button" type="submit" disabled={!question.trim() || status === 'loading'}>
          {status === 'loading' ? 'Answering…' : 'Ask'}
        </button>
      </form>
      <p className="suggestion-label">Try asking</p>
      <div className="suggested-questions" aria-label="Suggested questions">
        {suggestions.slice(0, 4).map((suggestion) => (
          <button type="button" key={suggestion} onClick={() => onQuestionChange(suggestion)}>
            {suggestion}
          </button>
        ))}
      </div>
      {error && <p className="query-error" role="alert">The API did not answer this question. Confirm the backend is running and VITE_API_BASE_URL is configured.</p>}
      <div aria-live="polite" aria-busy={status === 'loading'}>
      {status === 'loading' && <p>Looking up community data…</p>}
      {result && (
        <article className="query-answer">
          <div><span className="answer-label">Question</span><p>{result.question || question}</p></div>
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
      </div>
    </section>
  );
}

export default AskCommunity;
