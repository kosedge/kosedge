/**
 * CFB research previews — KosEdge house format, no writer byline.
 * Numbers come from frozen power SoT + N=10,000 win-total artifact.
 * Research language only. No KEI, PLAY, LEAN, or invented market lines.
 */

export const CFB_PREVIEW_AS_OF = "2026-08-31";
export const CFB_PREVIEW_PUBLISHED = "2026-08-31";

export type CfbTeamPreview = {
  slug: string;
  team: string;
  title: string;
  conference: string;
  date: string;
  bottomLine: string;
  theNumber: string;
  quickProjection: string;
  rosterSnapshot: string;
  whatMattersMost: string;
  scheduleNotes: string;
  bettingAngles: string;
  whatWouldChange: string;
  modelNote: string;
};

export type CfbConferencePreview = {
  slug: string;
  title: string;
  conference: string;
  date: string;
  bottomLine: string;
  contenders: string;
  sleepers: string;
  scheduleNotes: string;
  researchAngles: string;
  modelNote: string;
};

export const CFB_TEAM_PREVIEWS: CfbTeamPreview[] = [
  {
    slug: "osu",
    team: "OSU",
    title: "Ohio State 2026 season preview",
    conference: "Big Ten",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Frozen SoT still ranks Ohio State #1 in power (1.617) with the lowest early-season uncertainty among the top five. That is a talent claim, not a win-total claim — the post–Week-0 10,000-path board has the Buckeyes at 9.54 E[wins] (p10–p90 8–11), fifth in expected wins because the Big Ten slate is harder than ACC / Independent paths above them.",
    theNumber:
      "Research win band 8–11 (median 10, E[wins] 9.54). Power rank 1. No market line is published here; used_in_spread=false.",
    quickProjection:
      "Offense 1.65 / defense 1.59 on the composed index. Bowl probability 0.986 on the frozen slate. CFP / national-title percentages live on the futures artifact, not this preview.",
    rosterSnapshot:
      "QB Julian Sayin, class incumbent, not an open job. Efficiency source is packaged SP+ final 2025 (not a warehouse fill). Next: Week 1 home vs Ball State.",
    whatMattersMost:
      "Whether the dual-index lead holds after Week 1–3 actuals. The prior is 2025 SP+ plus roster/QB; a slow start against a soft opener would not, by itself, invert the power board.",
    scheduleNotes:
      "Week 1 BALL is on the official slate and opens in Project Game. Remaining Big Ten path is why E[wins] sits below Miami / Notre Dame / Oregon / Utah despite the #1 power rank.",
    bettingAngles:
      "Track market win totals vs the 8–11 research band after books post. Do not treat 9.54 as a bet. Week 1 vs Ball State is a research-fair project-game, not a PLAY.",
    whatWouldChange:
      "Sayin injury or a multi-week offensive-index collapse; a warehouse-fill swap (this row is packaged, not filled); or a slate revision that adds/removes a Power-4 home game.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "ore",
    team: "ORE",
    title: "Oregon 2026 season preview",
    conference: "Big Ten",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Oregon is #2 in power (1.563) and #3 in E[wins] (9.69, band 8–11). The portal QB prior (Dante Moore) is already in the index — uncertainty 0.325 is higher than Ohio State’s 0.215, which is the honest early-season gap, not a hidden downgrade.",
    theNumber:
      "Research win band 8–11 (median 10, E[wins] 9.69). Power rank 2. Research only.",
    quickProjection:
      "Offense 1.65 / defense 1.47. Bowl probability 0.988. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB Dante Moore, portal class, not open. Packaged SP+ 2025. Next: Week 1 home vs Boise State — a real G5 test, not an FCS placeholder.",
    whatMattersMost:
      "Week 1 vs Boise is the first live check on whether the #2 power row survives a competent G5 opponent. Project Game is the right surface; do not invent a spread here.",
    scheduleNotes:
      "Home vs BOISE is on the official Week 1 board. Oregon’s win-total rank sitting next to Ohio State is schedule-coherent, not a second rating.",
    bettingAngles:
      "Watch how books price ORE/BOISE versus the research-fair project-game once posted. Season win-total: compare the 8–11 band to the market when it exists. No lean is published.",
    whatWouldChange:
      "Moore not starting; a large Week 1 offensive miss vs Boise; or Big Ten slate changes that add another top-15 road game.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "miss",
    team: "MISS",
    title: "Ole Miss 2026 season preview",
    conference: "SEC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Ole Miss is the SEC’s top power row (#3 overall, 1.548) with a portal QB prior (Trinidad Chambliss). E[wins] 8.46 (band 7–10) ranks 12th — the SEC path taxes win totals more than the Independent / ACC slates above them.",
    theNumber:
      "Research win band 7–10 (median 9, E[wins] 8.46). Power rank 3. Research only.",
    quickProjection:
      "Offense 1.68 (highest among the top five) / defense 1.42. Bowl probability 0.979. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB Trinidad Chambliss, portal, not open. Packaged SP+ 2025. Next: Week 1 vs Louisville, tagged neutral on the official slate.",
    whatMattersMost:
      "The offensive-index lead is the identity. If Week 1 vs Louisville is a defensive slog, the power rank can still hold; a multi-week offensive miss would not.",
    scheduleNotes:
      "Neutral-site Week 1 vs LOU is a Project Game row (neutral=1). Remaining SEC games are why this is not a 10-win prior.",
    bettingAngles:
      "Track the Louisville opener as a research-fair number, not a conference-title proxy. Season band 7–10 vs any posted win total — pass if the market sits inside the band.",
    whatWouldChange:
      "Chambliss not starting; Week 1 injury; or a slate add that inserts another top-10 SEC road game.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "mia",
    team: "MIA",
    title: "Miami 2026 season preview",
    conference: "ACC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Miami is #4 in power (1.531) and #1 in E[wins] (10.15, band 9–12). That split is the product: ACC path + packaged efficiency, not a claim that Miami is more talented than Ohio State or Oregon.",
    theNumber:
      "Research win band 9–12 (median 10, E[wins] 10.15). Power rank 4. Research only.",
    quickProjection:
      "Offense 1.58 / defense 1.48 — more balanced than Ole Miss. Bowl probability 0.993. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB Darian Mensah, portal, not open. Packaged SP+ 2025. Next: Week 1 at Stanford.",
    whatMattersMost:
      "Whether the ACC slate stays as soft as the frozen board assumes. A 10.15 E[wins] is a schedule number. Power 1.53 is the talent number.",
    scheduleNotes:
      "Week 1 at STAN is on the official board. Miami’s win-total rank above Ohio State is not a G5-over-P4 inversion — both are Power-4, different paths.",
    bettingAngles:
      "Win-total markets that open at 10+ are inside this research band. Game-level: use Project Game for STAN, then Edge Board for live books only.",
    whatWouldChange:
      "Mensah not starting; ACC slate adding a second top-15 road week; or a large Week 1 miss at Stanford that updates the offensive index.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "nd",
    team: "ND",
    title: "Notre Dame 2026 season preview",
    conference: "Independent",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Notre Dame is the Independent that matters. Power #7 (1.502), E[wins] #2 (10.05, band 8–11). The win-total lead is schedule: Independent path plus a Week 1 Wisconsin game the board already prices as a home/neutral row. This is not a CFP selection model.",
    theNumber:
      "Research win band 8–11 (median 10, E[wins] 10.05). Power rank 7. Research only.",
    quickProjection:
      "Offense 1.64 / defense 1.37. Bowl probability 0.994. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB CJ Carr, incumbent, not open. Lowest uncertainty in the Independent bucket (0.229). Packaged SP+ 2025. Next: Week 1 vs Wisconsin, neutral_site=true on the official slate.",
    whatMattersMost:
      "The Independent label in the SoT also contains leftover mappings (North Texas, Missouri, Toledo, etc.). Notre Dame is the only Independent power row in the top 20. Filter and conference preview call that out.",
    scheduleNotes:
      "Week 1 WIS is a Project Game deep-link. Remaining path is why 10.05 E[wins] can sit above Ohio State without claiming a better roster.",
    bettingAngles:
      "Track posted win totals against 8–11. Week 1 vs Wisconsin: research-fair project-game only — no PLAY/LEAN language.",
    whatWouldChange:
      "Carr injury; a slate revision that adds two Power-4 road games; or the Independent mapping cleanup changing who else shares this bucket (does not change ND’s power index).",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "utah",
    team: "UTAH",
    title: "Utah 2026 season preview",
    conference: "Big 12",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Utah is the Big 12’s top power row (#9 overall, 1.484) and #4 in E[wins] (9.63, band 8–11). Portal QB Devon Dampier is in the prior. Week 1 is FCS Idaho — the win-total is not being earned against that opener; it is the rest of the Big 12 path plus the power index.",
    theNumber:
      "Research win band 8–11 (median 10, E[wins] 9.63). Power rank 9. Research only.",
    quickProjection:
      "Offense 1.62 / defense 1.35. Bowl probability 0.988. Futures live on the futures artifact (natty % is a separate futures line, not KEI).",
    rosterSnapshot:
      "QB Devon Dampier, portal, not open. Uncertainty 0.315. Packaged SP+ 2025. Next: Week 1 home vs FCS Idaho (not a Project Game FBS row).",
    whatMattersMost:
      "First FBS test after the FCS opener. Until then, treat 9.63 E[wins] as a slate-sim output, not new information from Week 1.",
    scheduleNotes:
      "FCS:IDHO is on the official Week 1 board but is not an FBS-vs-FBS Project Game. Use Teams → next FBS opponent once posted, or open a manual matchup.",
    bettingAngles:
      "Do not invent a spread on Idaho. Season band 8–11 is the number to track when Big 12 win totals post. No lean.",
    whatWouldChange:
      "Dampier not starting; a Big 12 slate add opposite Texas Tech / Arizona in the same month; or a large Week 2+ offensive miss.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "usf",
    team: "USF",
    title: "South Florida 2026 season preview",
    conference: "AAC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "USF is the honesty check. Power #42 (1.260) — not a top-10 talent row. Post–Week-0 E[wins] #15 (8.38, band 7–10) — no longer tied with Ohio State. Soft AAC path still helps the win total; power order stays OSU–ORE–MISS–MIA.",
    theNumber:
      "Research win band 7–10 (median 8, E[wins] 8.38). Power rank 42. Win-total std is tighter than OSU’s on the closed board.",
    quickProjection:
      "Offense 1.45 / defense 1.07 — the defensive index is why this is not a Power-4 row. Bowl probability 0.986. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB KJ Cooper, incumbent, not open. Uncertainty 0.234 (tighter than several P4 portal jobs). Packaged SP+ 2025. Next: Week 1 home vs FIU.",
    whatMattersMost:
      "Do not read the win table as a power table. USF is no longer an 8.88=OSU E[wins] trap. Power order stays OSU–ORE–MISS–MIA.",
    scheduleNotes:
      "Week 1 FIU is on the official slate. AAC path is still the win-total story; cupcake saturation + smaller year-shock narrowed the band vs OSU.",
    bettingAngles:
      "If a win-total market prices USF like a top-10 talent, that is a research conflict to track — still not a PLAY. Game-level: Project Game vs FIU, then live books on Edge Board.",
    whatWouldChange:
      "A Power-4 home-and-home landing on the official slate; Cooper injury; or a defensive-index update that pulls power out of the 40s.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "boise",
    team: "BOISE",
    title: "Boise State 2026 season preview",
    conference: "Mountain West",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Boise is the Mountain West’s top power row (#47, 1.239) and a real Week 1 test at Oregon. E[wins] 6.65 (band 5–8) is not a Group-of-X title claim — it already prices the Oregon road opener.",
    theNumber:
      "Research win band 5–8 (median 7, E[wins] 6.65). Power rank 47. Research only.",
    quickProjection:
      "Offense 1.35 / defense 1.13. Bowl probability 0.875. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB Maddux Madsen, incumbent, not open. Packaged SP+ 2025. Next: Week 1 at Oregon.",
    whatMattersMost:
      "Week 1 at Oregon is the first live calibration for both programs. A competitive score does not move Boise into the Power-4 talent tier; a blowout does not erase the MWC power lead.",
    scheduleNotes:
      "ORE @ home for Oregon / road for Boise is an official Week 1 FBS row — Project Game deep-link is live. Remaining MWC path is why 6.65 E[wins] can still be a bowl prior.",
    bettingAngles:
      "Track the Oregon opener as research-fair vs books. Do not invent a Boise season win-total lean from 6.65. KEI is the published Edge Board line when the game is on the slate.",
    whatWouldChange:
      "Madsen not starting; Oregon Week 1 injury on either side; or MWC slate adding another Power-4 road game.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "jmu",
    team: "JMU",
    title: "James Madison 2026 season preview",
    conference: "Sun Belt",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "James Madison is the third G5 preview: power #65 (1.149), E[wins] #22 (7.91, band 6–10). Open QB (Arrington Maiden, open_competition). Higher uncertainty (0.394) than the P4 incumbents. Win-total is a Sun Belt path, not a talent spike.",
    theNumber:
      "Research win band 6–10 (median 8, E[wins] 7.91). Power rank 65. Research only.",
    quickProjection:
      "Offense 1.12 / defense 1.18. Bowl probability 0.926. Futures live on the futures artifact.",
    rosterSnapshot:
      "QB Arrington Maiden, open competition. Packaged SP+ 2025. Next: Week 1 home vs Liberty.",
    whatMattersMost:
      "The open QB is the row’s honesty label. Until a starter sticks, treat the 7.91 E[wins] as wider than the p10–p90 band implies.",
    scheduleNotes:
      "Week 1 LIB is on the official slate. Sun Belt remaining path is why this sits mid-pack in expected wins and nowhere near Power-4 in power.",
    bettingAngles:
      "Track the Liberty opener in Project Game. Season band 6–10 vs any posted win total — default pass inside the band. No PLAY language.",
    whatWouldChange:
      "A named starter for 3+ weeks; Maiden not the guy; or a Power-4 road add on the official slate.",
    modelNote:
      "KosEdge CFB Model · engine cfb-season-engine-v0.15-power-sot · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
];

export const CFB_CONFERENCE_PREVIEWS: CfbConferencePreview[] = [
  {
    slug: "sec",
    title: "SEC 2026 conference preview",
    conference: "SEC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "The SEC is the deepest power conference on the frozen SoT: Ole Miss #3, Texas A&M #6, Texas #8, Oklahoma #10, Auburn #13, Alabama #16. Win totals compress because everyone plays each other. This is not a CFP bracket.",
    contenders:
      "Ole Miss (power 3, E[wins] 8.46, Trinidad Chambliss) is the index leader. Texas A&M (6 / 8.38, Marcel Reed) and Texas (8 / 7.56, Arch Manning) sit in the same talent band. Oklahoma (10 / 6.92, John Mateer) is the fourth row inside the top 10.",
    sleepers:
      "Auburn (#13, Byrum Brown) and Alabama (#16, Austin Mack) are still top-20 power. They are not G5 sleepers — they are SEC rows whose win totals get taxed by the same slate.",
    scheduleNotes:
      "Week 1: Ole Miss vs Louisville (neutral), Texas A&M vs Missouri State, Texas vs Texas State, Oklahoma vs UTEP, Alabama vs East Carolina. Several openers are not conference games.",
    researchAngles:
      "Use power order for talent, E[wins] for path. A 9-win SEC prior is rarer than a 9-win ACC/Independent prior on this board. Track Project Game on the official openers; Edge Board for books only.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "big-ten",
    title: "Big Ten 2026 conference preview",
    conference: "Big Ten",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Ohio State #1 and Oregon #2 are the talent ceiling. Indiana #5 is the 2025-holdover row (Josh Hoover prior) — not a G5 inversion. USC #11 and Washington #12 keep the West side in the top 15. Penn State is #20.",
    contenders:
      "Ohio State (1 / 9.54, Julian Sayin) and Oregon (2 / 9.69, Dante Moore). Indiana (5 / 8.42) is a real power row on this SoT, not a warehouse fill.",
    sleepers:
      "USC (Week 0 vs San Jose State — first live FBS game on the packaged board) and Washington. They are top-15 power, mid-win-total because of the same Big Ten path that holds Ohio State to 9.54 E[wins].",
    scheduleNotes:
      "Week 0: USC vs SJSU (closed). Week 1: Ohio State–Ball State, Oregon–Boise, Indiana–North Texas, Washington–Washington State, Penn State–Marshall.",
    researchAngles:
      "IU at power #5 will look loud if you only remember 2023. The SoT is 2025-efficiency + roster/QB. Flag it; do not silently rerank. Win totals are not inverted vs consensus talent once you separate path from power.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "acc",
    title: "ACC 2026 conference preview",
    conference: "ACC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Miami is the ACC talent and win-total leader (power 4, E[wins] 10.15). SMU #14, Clemson #18, Louisville #21, Virginia #22, NC State #27. The ACC is where expected wins run hot relative to power.",
    contenders:
      "Miami (Darian Mensah). SMU (Kevin Jennings, E[wins] 9.21) is the second ACC power row. Clemson (Christopher Vizzina) is #18 — still a contender in this conference, not on the national power board.",
    sleepers:
      "Virginia (#22, E[wins] 9.53) and NC State (#27, 8.08) are the schedule-driven ACC cluster. They are not top-10 talent.",
    scheduleNotes:
      "Week 0: Virginia vs NC State (closed). Week 1: Miami at Stanford, SMU at Florida State, Clemson at LSU. Those openers are the first live checks; LSU/FSU are not ACC games.",
    researchAngles:
      "If an ACC win total sits at 10+, compare it to the Miami 9–12 / SMU 8–11 bands before treating it as a research conflict. Edge Board is KEI vs market.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "big-12",
    title: "Big 12 2026 conference preview",
    conference: "Big 12",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Utah #9 is the power lead. Arizona #15, Texas Tech #17, BYU #24, TCU #28, Iowa State #30. Several Week 1 games are FCS — do not read those openers as conference information.",
    contenders:
      "Utah (Devon Dampier, E[wins] 9.63). Arizona (Noah Fifita, E[wins] 8.13) and Texas Tech (Will Hammond, E[wins] 9.11) are the next two power rows and both open against FCS.",
    sleepers:
      "BYU #24 and TCU #28 (TCU hosted North Carolina in Week 0 — closed). Iowa State #30.",
    scheduleNotes:
      "Week 0: TCU vs North Carolina (closed). Week 1 FCS openers: Utah–Idaho, Arizona–Northern Arizona, Texas Tech–Abilene Christian. First FBS tests come later.",
    researchAngles:
      "Utah’s 9.63 E[wins] is a path number. Power 1.48 is the talent number. Track remaining FBS openers in Project Game; skip inventing lines on FCS openers.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "independent",
    title: "Notre Dame / Independent 2026 note",
    conference: "Independent",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Notre Dame is the Independent product. Power #7, E[wins] #2 (10.05). UConn remains a true Independent. The SoT Independent bucket also still contains leftover mappings (Missouri, North Texas, Toledo, New Mexico, East Carolina, and others). Those teams are filtered to their 2026 affiliation on Teams; we do not silently rewrite their power index.",
    contenders:
      "Notre Dame (CJ Carr). That is the list for Independent talent.",
    sleepers:
      "UConn is the other true Independent on the display overlay. Army displays as AAC (2024+ affiliation). Do not treat leftover Independent labels as a sleeper conference.",
    scheduleNotes:
      "Notre Dame Week 1 vs Wisconsin (neutral on the official slate). UConn Week 1 vs FCS Lafayette.",
    researchAngles:
      "Use the Independent conference page for the ND note, not as a 14-team standings race. Overlay is documented in data/ops and on the Teams filter.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "aac",
    title: "AAC 2026 conference preview",
    conference: "AAC",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Group-of-X #1 in this ship: South Florida is the AAC power lead (#42) with post–Week-0 E[wins] #15 (8.38) — no longer the national 8.88=OSU trap. UTSA is #55 power / mid-pack E[wins]. Memphis and Tulane follow. This is a path conference, not a talent conference.",
    contenders:
      "USF (KJ Cooper). UTSA (Owen McCown) is the second AAC power row. Neither is a top-25 talent row on this SoT.",
    sleepers:
      "Memphis and Tulane. Their win totals will look better than their power ranks. That is the AAC pattern, not a bug.",
    scheduleNotes:
      "Week 0: Memphis at UNLV (closed). Week 1: USF vs FIU, UTSA’s opener is on the official board. North Texas displays as AAC (SoT still said Independent) and opens at Indiana — that is a Power-4 road, not an AAC cupcake.",
    researchAngles:
      "Any board that ranks USF / UTSA / USF-class teams above Power-4 in power is wrong. This board does not. E[wins] is allowed to look path-loud; the page banners it.",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
  {
    slug: "mountain-west",
    title: "Mountain West 2026 conference preview",
    conference: "Mountain West",
    date: CFB_PREVIEW_PUBLISHED,
    bottomLine:
      "Group-of-X #2: Boise State is the power lead (#47). Hawai'i #62 and UNLV #63 sit together. Hawai'i’s E[wins] (6.34) is a schedule number — power is 62nd, not inverted.",
    contenders:
      "Boise State (Maddux Madsen), with the Week 1 Oregon road already in the 6.65 E[wins]. UNLV (Jackson Arnold) is the second interesting MWC row.",
    sleepers:
      "Hawai'i (Micah Alejado) — win-total sleeper relative to power, not a top-20 talent sleeper. San Diego State and Utah State trail.",
    scheduleNotes:
      "Week 0: Hawai'i at Stanford and Memphis at UNLV (closed). Week 1: Boise at Oregon is the MWC event. New Mexico and Nevada / Colorado State display as MWC via overlay.",
    researchAngles:
      "Use Boise/Oregon as the research-fair Project Game. Do not promote Hawai'i into a top-20 talent conversation because of E[wins].",
    modelNote:
      "KosEdge CFB Model · N=10,000 · as_of 2026-08-31 · used_in_spread=false · KEI is a separate published line.",
  },
];

export function getCfbTeamPreviews(): CfbTeamPreview[] {
  return CFB_TEAM_PREVIEWS;
}

export function getCfbConferencePreviews(): CfbConferencePreview[] {
  return CFB_CONFERENCE_PREVIEWS;
}

export function findCfbTeamPreview(
  slugOrTeam: string,
): CfbTeamPreview | undefined {
  const key = String(slugOrTeam || "")
    .trim()
    .toLowerCase();
  return CFB_TEAM_PREVIEWS.find(
    (p) => p.slug === key || p.team.toLowerCase() === key,
  );
}

export function findCfbConferencePreview(
  slug: string,
): CfbConferencePreview | undefined {
  const key = String(slug || "")
    .trim()
    .toLowerCase();
  return CFB_CONFERENCE_PREVIEWS.find((p) => p.slug === key);
}
