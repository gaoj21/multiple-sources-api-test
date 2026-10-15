"""每个数据源要让模型找什么、只认哪些官方域名。

模型通过联网搜索去找; 程序事后会检查每条结果的链接是否落在 domains 里,
不在的会被标成 off_source, 不计入结果。
"""

# 付费数据源 (D&B、Orbis、Quartr、LexisNexis) 的数据在登录墙后面, 联网搜索看不到, 所以不在这里。
SOURCES = {
    "usaspending": {
        "name": "USAspending.gov",
        "domains": ["usaspending.gov"],
        "looks_for": "US federal contract and grant awards to this company (new awards, modifications, terminations), "
                     "with award ID, amount, awarding agency and action date",
        "event_types": ["contract_award", "grant_award", "modification", "termination"],
    },
    "sam": {
        "name": "SAM.gov",
        "domains": ["sam.gov"],
        "looks_for": "the company's SAM.gov entity registration (UEI, CAGE, status, expiration), any exclusion/debarment "
                     "record, and contract award notices naming it as awardee",
        "event_types": ["registration", "exclusion", "contract_award_notice"],
    },
    "grants": {
        "name": "Grants.gov",
        "domains": ["grants.gov"],
        "looks_for": "grant opportunities or notices that name this company (grant awards themselves are on USAspending)",
        "event_types": ["grant_opportunity"],
    },
    "govinfo": {
        "name": "GovInfo / Federal Register",
        "domains": ["govinfo.gov", "federalregister.gov"],
        "looks_for": "Federal Register documents or other US government publications that name this company: "
                     "agency orders, penalties, settlements, consent orders, rules, notices",
        "event_types": ["agency_order", "penalty", "settlement", "notice", "rule"],
    },
    "courtlistener": {
        "name": "CourtListener (US court records)",
        "domains": ["courtlistener.com", "storage.courtlistener.com", "uscourts.gov"],
        "looks_for": "US court cases where the company is a party: new lawsuits, bankruptcy filings, judgments, opinions, "
                     "with case name, docket number and court",
        "event_types": ["lawsuit_filed", "bankruptcy", "judgment", "opinion", "settlement"],
    },
    "doj": {
        "name": "US Department of Justice press releases",
        "domains": ["justice.gov"],
        "looks_for": "DOJ press releases naming the company: indictments, pleas, settlements, False Claims Act cases, "
                     "antitrust actions",
        "event_types": ["indictment", "plea", "settlement", "civil_action", "antitrust"],
    },
    "ftc": {
        "name": "Federal Trade Commission",
        "domains": ["ftc.gov"],
        "looks_for": "FTC press releases, cases and proceedings, consent orders, merger challenges and HSR "
                     "early-termination notices involving the company",
        "event_types": ["enforcement", "consent_order", "merger_challenge", "hsr_early_termination"],
    },
    "osha": {
        "name": "OSHA (US Department of Labor)",
        "domains": ["osha.gov", "dol.gov"],
        "looks_for": "OSHA inspections, citations, penalties and news releases for the company's US establishments",
        "event_types": ["inspection", "citation", "penalty"],
    },
    "ucc": {
        "name": "UCC filings (US state Secretary of State records)",
        "domains": ["sos.state.co.us", "data.colorado.gov", "data.ct.gov", "portal.ct.gov", "sos.ca.gov",
                    "bizfileonline.sos.ca.gov", "dos.ny.gov", "sos.texas.gov", "dos.fl.gov", "sunbiz.org",
                    "sos.delaware.gov", "ilsos.gov", "sos.wa.gov", "sos.mn.gov", "sos.ky.gov"],
        "looks_for": "UCC financing statements (UCC-1/UCC-3) where the company is the debtor: filing number, filing date, "
                     "secured party, collateral, lapse date",
        "event_types": ["ucc1_filing", "ucc3_amendment", "ucc3_termination", "continuation"],
    },
    "uspto": {
        "name": "USPTO (patents and trademarks)",
        "domains": ["uspto.gov", "patents.google.com", "tsdr.uspto.gov", "ppubs.uspto.gov"],
        "looks_for": "patents granted or applications published, and trademark filings, assigned to the company",
        "event_types": ["patent_grant", "patent_application", "trademark_filing"],
    },
    "earnings_calls": {
        "name": "Earnings call transcripts",
        # 公司自己的投资者关系网站也算 (程序会把公司官网域名加进来)
        "domains": ["fool.com", "seekingalpha.com", "investing.com", "nasdaq.com", "marketbeat.com",
                    "earningscall.biz", "quartr.com", "roic.ai", "alphastreet.com"],
        "looks_for": "earnings call transcripts or webcasts held in the window: date, fiscal period, key statements on "
                     "guidance, debt, liquidity, risks (only if the company is publicly listed)",
        "event_types": ["earnings_call"],
        "include_company_domain": True,
    },
}

# 额外任务: 找公司官网 (以及投资者关系页、新闻页)
WEBSITE_TASK = "company_website"
