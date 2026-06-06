"""100 unique human-domain questions for response adequacy audits.

Each domain has 10 questions spanning past, present, future, and how-to styles.
None duplicate the tech-news or religion-choice calibration examples.
"""

from __future__ import annotations

HUMAN_DOMAIN_QUESTIONS: dict[str, list[str]] = {
    "history_past": [
        "Why did the Roman Empire fall?",
        "What daily life was like for a medieval blacksmith?",
        "Who led the Haitian Revolution and what changed after it?",
        "What caused the Great Depression in the 1930s?",
        "How did the printing press change European politics?",
        "What was the Silk Road used for besides trade?",
        "Why was the Magna Carta signed?",
        "What happened during the Cuban Missile Crisis?",
        "How did ancient Egyptians mummify bodies?",
        "What role did codebreakers play in World War Two?",
    ],
    "present_world": [
        "What is happening with global shipping routes right now?",
        "How are electric vehicle sales trending this year?",
        "What is the current unemployment rate in the United States?",
        "Which countries are facing severe drought conditions now?",
        "What is going on with international space station missions today?",
        "How is the housing market behaving in major US cities lately?",
        "What vaccines are recommended for adults this season?",
        "Which films won major awards at the most recent ceremony?",
        "What is the status of the Panama Canal water levels?",
        "How are renewable energy investments performing recently?",
    ],
    "future_speculation": [
        "Will fusion power become commercially viable in the next twenty years?",
        "How might cities adapt if sea levels rise one meter?",
        "What jobs are most likely to be automated by 2035?",
        "Could humans establish a permanent base on Mars this century?",
        "What will happen to cash payments in a digital economy?",
        "How might antibiotic resistance change medicine in the future?",
        "Will remote work remain common after office trends shift?",
        "What could replace lithium in large-scale batteries?",
        "How might AI change classroom teaching ten years from now?",
        "Will global population growth peak before 2100?",
    ],
    "how_to_practical": [
        "How do I remove red wine stains from a cotton shirt?",
        "What is the proper way to sharpen a kitchen knife at home?",
        "How can I start a compost bin in a small apartment?",
        "How do I change a flat tire on a front-wheel drive car?",
        "What steps should I take to freeze fresh herbs?",
        "How do I calibrate a digital kitchen scale?",
        "How can I safely descale a kettle with household items?",
        "How do I patch a small hole in drywall?",
        "What is a simple method to organize cables behind a desk?",
        "How should I season a new cast iron skillet?",
    ],
    "health_body": [
        "Why do muscles feel sore a day after exercise?",
        "What is the difference between a sprain and a strain?",
        "How much sleep do teenagers typically need?",
        "What foods are high in iron for someone who is anemic?",
        "Why does caffeine make some people jittery?",
        "What are common signs of dehydration?",
        "How does fiber affect digestion?",
        "What is hypertension and why is it risky?",
        "Why do allergies get worse in spring for some people?",
        "What happens to the body during a fever?",
    ],
    "money_work": [
        "What is compound interest in simple terms?",
        "How does a 401k differ from an IRA?",
        "Why do central banks raise interest rates?",
        "What is inflation and who does it hurt most?",
        "How should someone negotiate a first salary offer?",
        "What does diversification mean in investing?",
        "Why do startups burn through cash quickly?",
        "What is a credit score used for?",
        "How do supply chains affect product prices?",
        "What skills help someone switch into data analysis?",
    ],
    "relationships_social": [
        "Why do long-distance relationships become difficult?",
        "How can two roommates split chores fairly?",
        "What makes an apology feel sincere?",
        "Why do people ghost instead of ending things directly?",
        "How do you support a friend who lost a parent?",
        "What is emotional labor in a partnership?",
        "Why do family arguments repeat the same patterns?",
        "How can shy people meet new friends as adults?",
        "What boundaries are healthy in workplace friendships?",
        "Why does active listening improve conflict resolution?",
    ],
    "science_nature": [
        "How do black holes bend light?",
        "Why is the sky blue on clear afternoons?",
        "What is photosynthesis and where does it happen?",
        "How do earthquakes generate tsunamis?",
        "Why do some metals rust and others do not?",
        "What is DNA and what does it store?",
        "How do vaccines train the immune system?",
        "Why do seasons change in temperate regions?",
        "What causes auroras near the poles?",
        "How do bees communicate food locations?",
    ],
    "arts_culture": [
        "What is impressionism in painting?",
        "Who wrote the novel One Hundred Years of Solitude?",
        "Why did jazz emerge in New Orleans?",
        "What is the difference between a sonnet and free verse?",
        "How did hip hop culture start in the Bronx?",
        "What makes Gothic cathedral architecture distinctive?",
        "Who composed the Four Seasons and when?",
        "What is method acting in theater?",
        "Why is the Parthenon historically significant?",
        "How did cinema transition from silent films to talkies?",
    ],
    "personal_ethics": [
        "Is it ever okay to tell a white lie to protect feelings?",
        "What does utilitarianism mean in ethics?",
        "Why do people feel guilt even when no one knows?",
        "What is the trolley problem trying to test?",
        "How do cultures define fairness differently?",
        "Is privacy a moral right or a legal one?",
        "Why do whistleblowers take personal risk?",
        "What is moral luck in philosophy?",
        "How should someone think about animal welfare?",
        "What does integrity mean in everyday decisions?",
    ],
}


def all_questions() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for domain, questions in HUMAN_DOMAIN_QUESTIONS.items():
        for q in questions:
            out.append((domain, q))
    return out
