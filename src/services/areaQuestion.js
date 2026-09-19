// Selected-tract answers use the same API-loaded values shown by the map.
// The query endpoint itself supports only the Fenton Village study area.
export function answerAreaQuestion(question, area) {
  const patterns = [
    [/population|residents|people live/i, ['total_population', 'population']],
    [/income|earn/i, ['median_household_income', 'income']],
    [/commut|transport|walk|bike/i, ['commute_active_share']],
    [/age/i, ['median_age']],
    [/rent|hous|own/i, ['renter_share']],
    [/language|multilingual/i, ['multilingual_household_share']],
  ];
  const keys = patterns.find(([pattern]) => pattern.test(question))?.[1];
  const overview = /overview|summary/i.test(question);
  const stats = (area.stats ?? []).filter((stat) => overview || keys?.includes(stat.id));
  const sourceIds = new Set(stats.flatMap((stat) => stat.sourceIds ?? []));
  return {
    question,
    answer: stats.length
      ? stats.map((stat) => `${stat.label}: ${stat.value}.`).join('\n')
      : 'This question is not available for the selected tract. Ask about population, income, age, renting, languages, or walking and cycling to work, or explore Fenton Village for study-area business questions.',
    evidence: (area.sources ?? []).filter((source) => sourceIds.has(source.id)).map((source) => ({
      organization: source.organization, dataset: source.dataset, dataset_year: source.year,
      geography: source.geography || area.areaName, source_variable: source.table, source_url: source.url,
    })),
    limitations: keys?.includes('commute_active_share')
      ? ['The loaded tract data reports walking or cycling to work; a full commute breakdown is not available here.'] : [],
  };
}
