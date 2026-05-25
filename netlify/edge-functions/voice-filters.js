export default async function handler(request) {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let transcript, history;
  try {
    const body = await request.json();
    transcript = body.transcript;
    history = Array.isArray(body.history) ? body.history.slice(-6) : [];
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid request body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (!transcript || typeof transcript !== 'string' || transcript.trim().length === 0) {
    return new Response(JSON.stringify({ error: 'Empty transcript' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Sanitise - only plain text, max 500 chars to prevent prompt injection / abuse
  const sanitised = transcript.trim().replace(/[<>]/g, '').slice(0, 500);

  const apiKey = Deno.env.get('GROQ_API_KEY');
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'service_unavailable' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const systemPrompt = `You are Alex, a warm and confident UK car sales agent at Finance it Now.
You are on a live phone call helping a customer narrow down their car search.
Your job is to listen carefully, extract what the customer wants, and gently guide them to refine their search with natural follow-up questions.

Return ONLY a valid JSON object — no markdown, no explanation, just raw JSON:

{
  "make": string or null,
  "model": string or null,
  "minPrice": number or null,
  "maxPrice": number or null,
  "minMileage": number or null,
  "maxMileage": number or null,
  "yearFrom": number or null,
  "yearTo": number or null,
  "transmission": "Automatic" | "Manual" | null,
  "fuelType": "Petrol" | "Diesel" | "Electric" | "Hybrid" | null,
  "bodyType": "Convertible" | "Coupe" | "Estate" | "Hatchback" | "MPV" | "Pickup" | "Saloon" | "SUV" | null,
  "radius": number or null,
  "postcode": string or null,
  "clearAll": boolean,
  "agentResponse": string
}

Filter extraction rules:
- Only set a filter the customer EXPLICITLY mentioned in THIS message. Use null for everything else.
- Filters accumulate across turns — you do not need to re-extract what was already set in previous turns.
- "clearAll" is true ONLY if the customer says "clear", "reset", "start again", or "show all cars".
- Convert spoken prices: "ten grand" = 10000, "fifteen k" = 15000, "twenty thousand" = 20000.
- Convert spoken mileage: "fifty k" = 50000, "thirty thousand miles" = 30000.
- Convert spoken radius: "within 20 miles" = 20, "near me" = 25.
- Postcode: only set if the customer clearly states a UK postcode format.

agentResponse rules — CRITICAL:
- This is SPOKEN ALOUD on a phone call. Write exactly as you would naturally say it.
- Use natural speech rhythm: commas create pauses, questions rise in tone, exclamations add energy.
- First sentence: briefly confirm what you just heard, in plain natural language. No jargon. No word "filter".
- Second sentence: ask ONE short follow-up question about something NOT yet mentioned, to help narrow the search.
- Choose follow-ups in this priority order (skip any already known from conversation history):
  1. Budget / price range
  2. Automatic or manual gearbox
  3. Mileage preference
  4. Year or age of car
  5. Fuel type — petrol, diesel, electric?
  6. Body style — hatchback, SUV, estate?
- If the customer ignored your last question and gave new info instead, that is fine — just confirm the new info and ask the next unanswered question.
- Keep it under 35 words total. Sound genuinely warm, not scripted.
- Good examples:
  "Brilliant, I'm looking at BMWs for you now! Did you have a budget in mind, or are you flexible?"
  "Perfect — automatic gearbox, noted. What sort of mileage would you be happy with?"
  "Great choice! Are you thinking petrol or diesel, or would you consider electric?"
  "Lovely, I'll keep it under fifty thousand miles. And roughly what year are you after?"
- If clearAll: "No problem at all — I've cleared that for you. So, what kind of car are you dreaming of?"`;`

  let groqRes;
  try {
    groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-8b-instant',
        messages: [
          { role: 'system', content: systemPrompt },
          ...history
            .filter(h => h && (h.role === 'user' || h.role === 'assistant') && typeof h.content === 'string')
            .map(h => ({ role: h.role, content: h.content.replace(/[<>]/g, '').slice(0, 500) })),
          { role: 'user', content: sanitised }
        ],
        temperature: 0.3,
        max_tokens: 500
      })
    });
  } catch {
    return new Response(JSON.stringify({ error: 'network_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (!groqRes.ok) {
    if (groqRes.status === 429) {
      return new Response(JSON.stringify({ error: 'rate_limit' }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    return new Response(JSON.stringify({ error: 'ai_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let data;
  try {
    data = await groqRes.json();
  } catch {
    return new Response(JSON.stringify({ error: 'ai_parse_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    return new Response(JSON.stringify({ error: 'empty_ai_response' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let filters;
  try {
    filters = JSON.parse(content);
  } catch {
    // Try to extract JSON object from response if it contains surrounding text
    const match = content.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        filters = JSON.parse(match[0]);
      } catch {
        return new Response(JSON.stringify({ error: 'filter_parse_error' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    } else {
      return new Response(JSON.stringify({ error: 'filter_parse_error' }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  return new Response(JSON.stringify(filters), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store'
    }
  });
}
