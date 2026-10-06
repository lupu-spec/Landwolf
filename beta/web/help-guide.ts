/** Reviewed app guidance with bounded, on-device retrieval; no generative model. */
export type HelpView =
  | "auth"
  | "account"
  | "explore"
  | "hunt"
  | "research"
  | "property"
  | "feedback"
  | "billing"
  | "sources";
export type HelpContext = {
  view: HelpView;
  authenticated: boolean;
  owner: boolean;
  access: boolean;
};
export type HelpStep = {
  view: HelpView;
  selector: string;
  title: string;
  detail: string;
};
export type HelpTopic = {
  id: string;
  title: string;
  keywords: string;
  steps: string[];
  tip: string;
  views: HelpView[];
  tour?: HelpStep[];
  owner?: boolean;
  accountAction?: "reset" | "profile";
};
export const MAX_QUESTION = 600;
export const SUPPORT_EMAIL = "support.landwolf@gmail.com";
const topics: HelpTopic[] = [
  {
    id: "start",
    title: "Get started",
    keywords:
      "start getting started first time beginner welcome hello hi romulus remus wolves brothers tour walkthrough help use app",
    views: ["auth"],
    steps: [
      "Create an account or sign in with your email and password.",
      "Open Explore properties for a one-time search, or Hunt to save your criteria.",
      "Open a property to review its evidence, research questions and deal scenario.",
    ],
    tip: "We’re Romulus (the black wolf) and Remus (the white wolf), your twin guides. Ask us to reset your password or update your profile. Account forms use your signed-in account and only save when you confirm.",
    tour: [
      {
        view: "auth",
        selector: "#register-tab",
        title: "Choose your account action",
        detail:
          "Choose Create account if you are new, or Sign in if you already have an account.",
      },
      {
        view: "auth",
        selector: "#auth-form",
        title: "Enter your details",
        detail:
          "Use your email and a unique password of 12–128 characters. Enter them in the account form, never in chat.",
      },
      {
        view: "auth",
        selector: "#auth-submit",
        title: "Continue to LandWolf",
        detail:
          "Submit the form yourself. Creating an account does not start a charge. Membership shows any access requirements.",
      },
    ],
  },
  {
    id: "login",
    title: "Sign in or recover access",
    keywords:
      "login log in sign in password reset forgot account email verification verify locked access account recovery",
    views: ["auth", "account"],
    accountAction: "reset",
    steps: [
      "Use Sign in with the email you registered and your password.",
      "Choose Request password reset here, or Forgot password? on the sign-in screen.",
      "Confirm the email request, then open the single-use link sent to your account email to choose a new password.",
      "If email delivery is unavailable, use Contact support for account assistance.",
    ],
    tip: "Do not share passwords, reset links, card numbers or session details with us. Password reset links expire and a completed reset signs out existing sessions.",
  },
  {
    id: "profile",
    title: "Update my profile",
    keywords:
      "update edit change correct profile personal data details information contact name company phone number job title industry role goals preferences crm email",
    views: ["billing", "account"],
    accountAction: "profile",
    steps: [
      "Sign in, then choose Review my profile here to open your own CRM details.",
      "Edit your name, company, phone, job title, industry, role, intended use or product-news preference.",
      "Choose Review my changes, check the summary, then Save my changes.",
    ],
    tip: "We only save fields you review in the account form. This does not delete your account or CRM history. Login email corrections require support; billing and owner access controls are not editable here.",
  },
  {
    id: "no-delete",
    title: "Account data cannot be deleted in chat",
    keywords: "delete erase purge remove account profile data record history",
    views: [],
    steps: [
      "Romulus and Remus can help correct your profile or request a password reset.",
      "Chat cannot delete accounts, CRM contacts or their history. Contact support for other account requests.",
    ],
    tip: "Your request has not deleted or changed anything. Profile changes always require your review and confirmation in an account form.",
  },
  {
    id: "session",
    title: "Stay signed in",
    keywords:
      "stay signed logged login persistent remember cookie cache browser restart logout log out sign out",
    views: ["auth", "billing"],
    steps: [
      "Sign in in your regular browser and allow this site to retain cookies.",
      "You can close the browser and return; active sessions renew when you return to the app.",
      "Choose Sign out when you want to end the session.",
    ],
    tip: "Deleting site cookies, private-browsing cleanup, a password reset, server revocation or session expiry requires another sign-in. Cache-only clearing is different from deleting cookies.",
  },
  {
    id: "search",
    title: "Find properties",
    keywords:
      "search find properties land listings explore filters state county acres acreage budget price sort browse buy land",
    views: ["explore"],
    steps: [
      "Open Explore properties and choose a state, or keep the nationwide view.",
      "Set location, minimum acreage, price or category filters that matter to you.",
      "Run the search, then open a property card to review the original source and evidence.",
    ],
    tip: "A missing acreage or price will not pass that numeric filter. A published bid, tax balance or asking price is not a verified market value.",
    tour: [
      {
        view: "explore",
        selector: '#search-form [name="state"]',
        title: "Choose your area",
        detail: "Choose a state, or keep US for the nationwide view.",
      },
      {
        view: "explore",
        selector: "#search-form",
        title: "Narrow your search",
        detail:
          "Enter the location, acreage, price and category filters you need. Leave optional filters open to see more results.",
      },
      {
        view: "explore",
        selector: "#search-submit",
        title: "Run your search",
        detail:
          "Select Search properties yourself, then open a result to investigate it. We never submit forms for you.",
      },
    ],
  },
  {
    id: "empty",
    title: "Troubleshoot missing results",
    keywords:
      "no results empty missing listings nothing found search blank fewer filters zero matches no matches",
    views: ["explore", "hunt"],
    steps: [
      "Try a broader state or location and remove optional price or acreage limits.",
      "Check whether your sale category and acreage range are too restrictive.",
      "Retry if the app reports a temporary request failure.",
    ],
    tip: "LandWolf displays partial public-source inventory. No matches does not prove that no land exists for sale. Unknown price or acreage and expired sales can exclude a listing.",
  },
  {
    id: "hunt",
    title: "Save a Hunt",
    keywords:
      "hunt hunts save saved search save criteria save filters create hunt acreage band edit hunt rename saved list",
    views: ["hunt"],
    steps: [
      "Open Hunt. Choose a state, an acreage band and an optional budget.",
      "Select Save Hunt & view matches. Wait for the saved confirmation.",
      "Your Hunt appears in Your saved Hunts. Reopen it to see matches or edit its criteria.",
    ],
    tip: "Hunts save your criteria. A match request can fail after the Hunt was successfully saved; use the match retry instead of creating a duplicate. The old separate Saved-property feature is retired.",
    tour: [
      {
        view: "hunt",
        selector: '#hunt-form [name="state"]',
        title: "Choose a state",
        detail: "Pick the state for this Hunt.",
      },
      {
        view: "hunt",
        selector: '#hunt-form [name="size"]',
        title: "Choose an acreage band",
        detail:
          "Use a preset size band. Advanced criteria provide custom acreage and more filters.",
      },
      {
        view: "hunt",
        selector: '#hunt-form [name="max_price"]',
        title: "Set an optional budget",
        detail:
          "Enter a budget or leave it blank. Auction budgets refer to the bid, not total project cost.",
      },
      {
        view: "hunt",
        selector: "#hunt-submit",
        title: "Save the Hunt",
        detail:
          "Select Save Hunt & view matches and wait for confirmation. We do not save or change your criteria on your behalf.",
      },
      {
        view: "hunt",
        selector: "#hunt-list",
        title: "Find it again",
        detail:
          "Your saved Hunts appear here after a successful save. Open a Hunt to review its results or edit it.",
      },
    ],
  },
  {
    id: "alerts",
    title: "Hunt changes and alerts",
    keywords:
      "alerts notifications changes automatic email updates schedule watch monitor hunt change checks",
    views: ["hunt"],
    steps: [
      "Open a saved Hunt to check its current matching inventory.",
      "Review the in-app changes and reconsideration prompts associated with that Hunt.",
      "Open the original source before relying on a listing’s dates or availability.",
    ],
    tip: "Scheduled Hunt emails and automatic email alerts are not enabled. Reconsideration uses existing inventory and your recorded research when you open the workspace.",
  },
  {
    id: "map",
    title: "Understand the map",
    keywords:
      "map maps pin pins marker coordinates parcel outline boundary boundaries location satellite missing point",
    views: ["explore", "research"],
    steps: [
      "Use the map/list controls in Explore properties to change the results layout.",
      "Open a pin or a list card to review a property.",
      "If a record has no validated source coordinates, use its list card and source link.",
    ],
    tip: "LandWolf does not invent pins or promise parcel outlines. An approximate address lookup is a reference point, not a surveyed property boundary.",
  },
  {
    id: "research",
    title: "Research a location",
    keywords:
      "research location address coordinates flood fema elevation soils soil census public records parcel geographic geocode",
    views: ["research"],
    steps: [
      "Open Property research. Choose an address or coordinates.",
      "Enter a complete street address or a verified latitude and longitude, then select Research location.",
      "Review each source’s facts, dates and limitations independently.",
    ],
    tip: "Missing flood information means unknown risk. An address lookup can fall on a road or a neighboring parcel. Research responses do not verify title, legal access or market value.",
    tour: [
      {
        view: "research",
        selector: "#research-mode",
        title: "Choose the location format",
        detail: "Select a complete street address or verified coordinates.",
      },
      {
        view: "research",
        selector: "#research-address, #research-latitude",
        title: "Enter your location",
        detail:
          "Use a complete address, or fill both latitude and longitude. A county or tract name is not a verified parcel location.",
      },
      {
        view: "research",
        selector: "#research-submit",
        title: "Research the location",
        detail:
          "Select Research location. Read each source’s limitations; an unavailable source does not establish low risk.",
      },
    ],
  },
  {
    id: "scenario",
    title: "Run a deal scenario",
    keywords:
      "scenario analysis simulate simulation roi profit loss return bid purchase price costs resale zero assumptions model numbers calculate",
    views: ["property"],
    steps: [
      "Open a property and find Build your deal scenario.",
      "Review purchase/bid, resale ranges and every cost assumption; replace placeholders with your researched inputs.",
      "Acknowledge the zero-cost warning when applicable, then choose Run 10,000 scenarios.",
    ],
    tip: "The bid-based resale defaults and zero costs are assumptions. Results are model outputs, not predictions or a recommendation to buy. Scenario drafts can disappear on reload or sign-out.",
    tour: [
      {
        view: "property",
        selector: '#analysis-form [name="purchase_price"]',
        title: "Review the acquisition price",
        detail:
          "Open a property first. Confirm whether the displayed amount is an asking price, minimum bid or another price type.",
      },
      {
        view: "property",
        selector: "#analysis-form",
        title: "Review all assumptions",
        detail:
          "Check resale ranges, holding time, financing and costs. Unknown costs are not confirmed zero costs.",
      },
      {
        view: "property",
        selector: "#run-analysis",
        title: "Run the scenario",
        detail:
          "After reviewing the assumptions and required warning, submit the scenario yourself. Treat the output as conditional on those inputs.",
      },
    ],
  },
  {
    id: "decision",
    title: "Record property research",
    keywords:
      "save research record research decision evidence questions goals requirements intended use cost allowance pause reconsider notes save property",
    views: ["property"],
    steps: [
      "Open a property and its Decision research workspace.",
      "Set your intended use, requirements and budget. Record evidence and known or unresolved costs.",
      "Select Record research to retain these inputs. Calculate preview only updates the displayed calculation.",
    ],
    tip: "Recorded research is private to your account. Link it to a Hunt to work with its shared goal; changing the source report or preview alone does not save your decision inputs.",
  },
  {
    id: "compare",
    title: "Compare Hunt research",
    keywords:
      "compare comparison two properties shared goal shared brief hunt research budget authority question reuse",
    views: ["hunt"],
    steps: [
      "Open a saved Hunt and update its research goal if needed.",
      "Link property research records to that Hunt and record your inputs.",
      "Use the Hunt’s comparison and shared research brief to review two recorded properties and open questions.",
    ],
    tip: "Shared questions do not automatically prove the same answer applies to every property. Confirm the planning authority and property applicability of evidence.",
  },
  {
    id: "print",
    title: "Print a research packet",
    keywords:
      "print pdf packet report download research export research brief printer paper",
    views: ["property", "hunt"],
    steps: [
      "Open a property’s recorded research or a Hunt’s shared research brief.",
      "Choose Print displayed research or Print shared research brief.",
      "Use your browser’s print dialog. Choose Save as PDF if your device offers it.",
    ],
    tip: "Review the displayed inputs before printing. Printing is different from recording research, and your device controls the output destination.",
  },
  {
    id: "membership",
    title: "Manage membership",
    keywords:
      "membership billing stripe subscribe subscription pay payment paywall pricing price monthly annual yearly complimentary access upgrade",
    views: ["billing"],
    steps: [
      "Open Membership to see the account’s current access and available options.",
      "Choose an offered plan only if you want to subscribe; review Stripe’s checkout before confirming.",
      "Use the billing portal control for an existing subscription when available.",
    ],
    tip: "Creating an account does not start a charge. Accepted eligible feedback pilots and owner-granted complimentary access follow their own access rules. We cannot inspect or change your billing account.",
  },
  {
    id: "cancel",
    title: "Cancel or change a subscription",
    keywords:
      "cancel cancellation stop subscription charges refund payment card manage billing portal",
    views: ["billing"],
    steps: [
      "Open Membership while signed in to the correct account.",
      "Open the billing portal if it is available for your subscription.",
      "Review and confirm the change in Stripe. If the portal is unavailable, contact support.",
    ],
    tip: "A chat message does not cancel a subscription or issue a refund. Check the billing portal for the effective date and confirmation.",
  },
  {
    id: "feedback",
    title: "Complete your feedback pilot",
    keywords:
      "feedback survey surveys pilot invite invitation consent accept overdue grace expired paused access three months check in",
    views: ["feedback"],
    steps: [
      "Open Feedback to see your own invitation, pilot status or due survey.",
      "If invited, review the terms and complete the starting survey to accept.",
      "Submit each due check-in using the feedback form and wait for the saved confirmation.",
    ],
    tip: "Pilots last three calendar months from acceptance, with check-ins on days 14, 30, 60 and 85. Overdue feedback can pause access. A pilot never automatically starts a paid subscription.",
  },
  {
    id: "users",
    title: "Export feedback users",
    keywords:
      "users user list export users csv download accounts invite users feedback admin owner",
    views: ["feedback"],
    owner: true,
    steps: [
      "Open Feedback while signed in to the configured owner account.",
      "In Manage investor feedback pilots, choose Export users CSV.",
      "Check your browser’s downloads. The file contains emails, roles and pilot dates.",
    ],
    tip: "The export is owner-only and includes up to 10,000 users. The on-screen account table shows up to 500. Your browser determines the download folder; this chat never reads the user list.",
  },
  {
    id: "coverage",
    title: "Inspect data coverage",
    keywords:
      "coverage sources diagnostics connected feeds refresh status inventory counts source failed connection",
    views: ["sources"],
    owner: true,
    steps: [
      "Open Data coverage with the configured owner account.",
      "Inspect source status, last successful refresh and the available state/category information.",
      "Use the original publisher links to confirm availability and sale terms.",
    ],
    tip: "Diagnostics are owner-only. Customer searches and Hunts still use connected inventory. A healthy source is not proof of complete nationwide inventory or verified property facts.",
  },
  {
    id: "support",
    title: "Contact support",
    keywords:
      "support contact human person help desk bug broken error problem email assistance report issue",
    views: ["account"],
    steps: [
      "Open About & privacy in this chat, then choose Contact support to open your email app.",
      "Describe which screen or control you used and the visible error message.",
      "Leave out passwords, payment card data and password-reset links.",
    ],
    tip: `LandWolf support is ${SUPPORT_EMAIL}. Your message is only sent when you send it in your email app.`,
  },
];
const stop = new Set(
  "a an the i me my we you your to for from of in on it is are do does can how what where when with and or please help want need this that tell about have get would could should be".split(
    " ",
  ),
);
export function helpTokens(text: string): string[] {
  return text
    .toLowerCase()
    .normalize("NFKC")
    .replace(/log\s*in|sign\s*in/g, " login ")
    .replace(/log\s*out|sign\s*out/g, " logout ")
    .replace(/walk\s*through/g, " walkthrough ")
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((word) => word.length > 1 && !stop.has(word))
    .slice(0, 60);
}
export function availableTopics(context: HelpContext): HelpTopic[] {
  return topics.filter(
    (topic) => !topic.owner || (context.authenticated && context.owner),
  );
}
export function suggestedTopics(context: HelpContext): HelpTopic[] {
  const preferred = availableTopics(context).filter((topic) =>
    topic.views.includes(context.view),
  );
  return [
    ...preferred,
    ...availableTopics(context).filter(
      (topic) =>
        topic.id === (context.authenticated ? "hunt" : "start") ||
        topic.id === "support",
    ),
  ]
    .filter(
      (topic, index, all) =>
        all.findIndex((item) => item.id === topic.id) === index,
    )
    .slice(0, 4);
}
export type HelpAnswer = {
  kind: "answer" | "clarify" | "fallback" | "invalid";
  topics: HelpTopic[];
};
export function answerHelp(
  question: string,
  context: HelpContext,
  previous?: string,
): HelpAnswer {
  if (!question.trim() || question.length > MAX_QUESTION)
    return { kind: "invalid", topics: [] };
  const allowed = availableTopics(context);
  const words = new Set(helpTokens(question));
  const deleting = ["delete", "erase", "purge", "remove"].some((word) =>
    words.has(word),
  );
  if (
    deleting &&
    ["account", "profile", "data", "record", "history"].some((word) =>
      words.has(word),
    )
  ) {
    return {
      kind: "answer",
      topics: allowed.filter((topic) => topic.id === "no-delete"),
    };
  }
  if (
    words.has("password") &&
    ["reset", "forgot", "forgotten", "change", "update"].some((word) =>
      words.has(word),
    )
  ) {
    return {
      kind: "answer",
      topics: allowed.filter((topic) => topic.id === "login"),
    };
  }
  if (
    /^(next|more|tell me more|what next|what about that)[?.!\s]*$/i.test(
      question.trim(),
    ) &&
    previous
  ) {
    const last = allowed.find((topic) => topic.id === previous);
    if (last) return { kind: "answer", topics: [last] };
  }
  const query = [...new Set(helpTokens(question))];
  const ranked = allowed
    .map((topic) => {
      const words = new Set(helpTokens(topic.keywords + " " + topic.title));
      const matches = query.filter((word) => words.has(word));
      const title = helpTokens(topic.title).join(" ");
      const exact =
        query.join(" ") === title ||
        (title.length > 5 && query.join(" ").includes(title));
      // Inverse document frequency favors specific controls over generic app words.
      const score =
        matches.reduce(
          (sum, word) =>
            sum +
            Math.log(
              1 +
                topics.length /
                  (1 +
                    topics.filter((t) => helpTokens(t.keywords).includes(word))
                      .length),
            ),
          0,
        ) +
        (exact ? 8 : 0) +
        (matches.length && topic.views.includes(context.view) ? 0.35 : 0);
      return { topic, score, matches: matches.length, exact };
    })
    .filter(
      (row) =>
        row.exact ||
        row.matches >= 2 ||
        (query.length === 1 && row.matches === 1 && row.score >= 1.5),
    );
  ranked.sort(
    (a, b) => b.score - a.score || a.topic.id.localeCompare(b.topic.id),
  );
  const best = ranked[0];
  if (!best) return { kind: "fallback", topics: suggestedTopics(context) };
  const second = ranked[1];
  if (second && !best.exact && second.score >= best.score * 0.82)
    return {
      kind: "clarify",
      topics: ranked.slice(0, 3).map((row) => row.topic),
    };
  return { kind: "answer", topics: [best.topic] };
}
