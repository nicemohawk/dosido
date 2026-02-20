"""Generate attendees and compatibility matrix for development testing.

Uses real climate tech / climate philanthropy figures (first name + last initial)
with curated attributes reflecting their actual backgrounds.
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from itertools import combinations
from pathlib import Path

# fmt: off
PEOPLE = [
    # --- Climate tech founders (from tech) ---
    {"name": "Peter R.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["carbon removal", "agriculture"], "top_climate_area": "carbon removal",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Built Segment to $3B exit, now turning biomass into carbon-negative hydrogen",
     "intention_90_day": "Scale bio-oil injection to 10x current sequestration volume",
     "matching_summary": "Peter R. is a repeat founder (ex-Segment CEO) building Charm Industrial, which converts biomass into bio-oil for permanent carbon removal. Looking for a GTM cofounder to scale enterprise carbon credit sales."},
    {"name": "Leah E.", "role": "science", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["sustainable materials", "carbon removal"], "top_climate_area": "sustainable materials",
     "commitment": "full-time", "arrangement": "colocated", "location": "Boston",
     "stage": "first-time-founder", "superpower": "Invented electrochemical process to make cement without CO2 emissions",
     "intention_90_day": "Close Series B and break ground on first commercial plant",
     "matching_summary": "Leah E. is a materials scientist building Sublime Systems, replacing fossil fuels in cement production with an electrochemical process. Looking for GTM help to land first major construction partnerships."},
    {"name": "Tim L.", "role": "engineering", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["energy", "grid infrastructure"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "Austin",
     "stage": "first-time-founder", "superpower": "Pioneering horizontal drilling for next-gen geothermal energy",
     "intention_90_day": "Complete first commercial enhanced geothermal well in Utah",
     "matching_summary": "Tim L. is an engineer building Fervo Energy, applying oil & gas horizontal drilling techniques to unlock geothermal power anywhere. Looking for an ops leader to manage field operations at scale."},
    {"name": "Mateo J.", "role": "engineering", "role_needed": "science", "lane": "idea",
     "climate_areas": ["energy", "grid infrastructure"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "Boston",
     "stage": "repeat-founder", "superpower": "Ex-Tesla energy storage lead, now building iron-air batteries for 100-hour storage",
     "intention_90_day": "Deliver first grid-scale iron-air battery to a utility partner",
     "matching_summary": "Mateo J. led Tesla's energy storage division before co-founding Form Energy, building ultra-cheap iron-air batteries for multi-day grid storage. Seeks a battery science researcher to push chemistry limits."},
    {"name": "Jigar S.", "role": "gtm", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "climate finance", "energy"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "repeat-founder", "superpower": "Invented the solar-as-a-service model, now directing $400B in DOE clean energy loans",
     "intention_90_day": "Accelerate loan disbursement for grid-scale storage and clean hydrogen projects",
     "matching_summary": "Jigar S. founded SunEdison and pioneered solar financing before leading the DOE Loan Programs Office. Deep GTM and finance expertise in clean energy deployment."},
    {"name": "Lynn J.", "role": "gtm", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "energy", "grid infrastructure"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Built the largest residential solar company in the US",
     "intention_90_day": "Launch virtual power plant product aggregating home batteries",
     "matching_summary": "Lynn J. co-founded and led Sunrun to a $4B public company, making rooftop solar accessible to millions. Looking for an engineering cofounder for next venture in distributed energy."},
    {"name": "Danielle F.", "role": "science", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["energy", "hydrogen"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "remote-open", "location": "SF",
     "stage": "first-time-founder", "superpower": "PhD dropout who built compressed air energy storage at 22",
     "intention_90_day": "Explore next venture in long-duration energy storage",
     "matching_summary": "Danielle F. founded LightSail Energy to store grid energy in compressed air. Deep physics background with a talent for making hard science investable."},
    {"name": "Kiran B.", "role": "product", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["energy", "grid infrastructure", "solar"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "repeat-founder", "superpower": "Built the platform connecting consumers to clean energy without rooftop solar",
     "intention_90_day": "Expand community solar marketplace to 15 new states",
     "matching_summary": "Kiran B. founded Arcadia, the largest platform for community solar and clean energy access. Product leader looking for engineering depth to build next-gen grid management tools."},
    {"name": "Danny K.", "role": "gtm", "role_needed": "product", "lane": "idea",
     "climate_areas": ["solar", "climate finance"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "remote-open", "location": "SF",
     "stage": "repeat-founder", "superpower": "Serial solar entrepreneur who built the global clean energy incubator network",
     "intention_90_day": "Launch climate finance product for emerging market solar developers",
     "matching_summary": "Danny K. co-founded Sungevity and now leads New Energy Nexus, the world's largest network of clean energy incubators. GTM expert looking for a product cofounder."},
    {"name": "Etosha C.", "role": "science", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["carbon removal", "sustainable materials"], "top_climate_area": "carbon removal",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "first-time-founder", "superpower": "Invented technology to turn CO2 into jet fuel and chemicals",
     "intention_90_day": "Secure first airline offtake agreement for CO2-derived sustainable aviation fuel",
     "matching_summary": "Etosha C. co-founded Twelve, using electrochemistry to convert captured CO2 into fuels and chemicals. Scientist seeking GTM partner to commercialize at scale."},
    {"name": "Priyanka B.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["circular economy", "sustainable materials"], "top_climate_area": "circular economy",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "first-time-founder", "superpower": "Built chemical recycling plants turning plastic waste into fuel and wax",
     "intention_90_day": "Commission third Brightmark plastics-to-fuel facility",
     "matching_summary": "Priyanka B. founded Brightmark to solve plastic waste through advanced chemical recycling. MIT-trained engineer looking for GTM expertise to scale partnerships with consumer brands."},
    {"name": "Cathy Z.", "role": "ops", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["EVs", "transport", "energy"], "top_climate_area": "EVs",
     "commitment": "full-time", "arrangement": "colocated", "location": "LA",
     "stage": "operator", "superpower": "Ran DOE efficiency programs under Obama, then scaled the largest US EV charging network",
     "intention_90_day": "Double EVgo fast-charging station count in underserved corridors",
     "matching_summary": "Cathy Z. served as DOE Assistant Secretary before leading EVgo's nationwide EV charging buildout. Operations expert with deep policy connections."},
    {"name": "Alex L.", "role": "product", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["energy", "buildings"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Built the behavioral science platform that saved 30 TWh of energy",
     "intention_90_day": "Launch new venture applying behavioral science to building decarbonization",
     "matching_summary": "Alex L. co-founded Opower (acquired by Oracle), using behavioral nudges to reduce home energy use at scale. Product visionary exploring next climate startup."},
    {"name": "Ryan O.", "role": "product", "role_needed": "engineering", "lane": "joiner",
     "climate_areas": ["carbon removal", "climate finance"], "top_climate_area": "climate finance",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "operator", "superpower": "Ex-Stripe product lead who built Watershed's carbon accounting platform",
     "intention_90_day": "Ship automated Scope 3 emissions tracking for enterprise customers",
     "matching_summary": "Ryan O. went from Stripe to Watershed, building the enterprise platform for measuring and reducing corporate carbon footprints. Product leader seeking engineering depth."},
    {"name": "Nan R.", "role": "ops", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["carbon removal", "climate finance"], "top_climate_area": "carbon removal",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "operator", "superpower": "Built Stripe Climate's frontier carbon removal portfolio from scratch",
     "intention_90_day": "Expand Frontier's advance market commitment to $2B in carbon removal purchases",
     "matching_summary": "Nan R. leads Stripe Climate and the Frontier carbon removal buyer coalition. Operations leader with unique expertise in carbon credit market design."},
    {"name": "Patrick B.", "role": "science", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["food", "agriculture"], "top_climate_area": "food",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Stanford biochemist who created the plant-based burger that bleeds",
     "intention_90_day": "Achieve price parity with conventional ground beef in US retail",
     "matching_summary": "Patrick B. founded Impossible Foods, using heme protein to make plant-based meat indistinguishable from animal products. Scientist-founder looking for ops help to scale manufacturing."},
    {"name": "Saul G.", "role": "engineering", "role_needed": "policy", "lane": "idea",
     "climate_areas": ["buildings", "solar", "EVs", "grid infrastructure"], "top_climate_area": "buildings",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "MacArthur genius who mapped the path to electrify everything in America",
     "intention_90_day": "Get 5 more states to adopt building electrification incentive programs",
     "matching_summary": "Saul G. founded Rewiring America, making the case that household electrification is the fastest path to decarbonization. Engineer and inventor seeking policy expertise to drive adoption."},
    {"name": "Tom S.", "role": "gtm", "role_needed": "science", "lane": "idea",
     "climate_areas": ["climate finance", "energy", "policy"], "top_climate_area": "climate finance",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Billionaire investor turned climate activist and political organizer",
     "intention_90_day": "Deploy $500M into climate infrastructure projects via Galvanize Climate Solutions",
     "matching_summary": "Tom S. founded NextGen America and Galvanize Climate Solutions, deploying billions into climate policy and clean energy infrastructure. GTM and finance leader seeking science-driven deal flow."},
    {"name": "Gia S.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["energy", "water", "biodiversity"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "first-time-founder", "superpower": "Built fish-safe hydropower turbines that generate clean energy without killing wildlife",
     "intention_90_day": "Deploy Restoration Hydro Turbines at 3 new dam sites",
     "matching_summary": "Gia S. co-founded Natel Energy, designing hydropower turbines that let fish pass safely. Engineer bridging renewable energy and ecosystem restoration."},
    # --- Climate investors from tech ---
    {"name": "Chris S.", "role": "gtm", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["carbon removal", "energy", "transport"], "top_climate_area": "carbon removal",
     "commitment": "exploring", "arrangement": "remote-open", "location": "LA",
     "stage": "repeat-founder", "superpower": "Early Twitter/Uber investor now deploying $800M into climate solutions",
     "intention_90_day": "Close Lowercarbon Fund III targeting hard-to-abate sectors",
     "matching_summary": "Chris S. co-founded Lowercarbon Capital after early bets on Twitter and Uber. Investing across the climate stack from direct air capture to EV infrastructure."},
    {"name": "John D.", "role": "gtm", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["energy", "climate finance", "policy"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "operator", "superpower": "Legendary VC who wrote Speed & Scale, the climate action playbook",
     "intention_90_day": "Catalyze $10B in follow-on investment for KPCB climate portfolio companies",
     "matching_summary": "John D. is the legendary Kleiner Perkins investor behind Google and Amazon, now fully focused on climate through Speed & Scale. Seeking science breakthroughs to back."},
    {"name": "Vinod K.", "role": "engineering", "role_needed": "science", "lane": "idea",
     "climate_areas": ["energy", "sustainable materials", "food"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "repeat-founder", "superpower": "Sun Microsystems co-founder placing big bets on impossible climate technologies",
     "intention_90_day": "Fund 5 new climate deep-tech companies through Khosla Ventures",
     "matching_summary": "Vinod K. co-founded Sun Microsystems and now runs Khosla Ventures, one of the most aggressive climate tech investors. Backs moonshot technologies others consider too risky."},
    {"name": "Nancy P.", "role": "gtm", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["solar", "transport", "climate finance"], "top_climate_area": "solar",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "operator", "superpower": "Early Tesla and SolarCity investor who proved climate investing generates returns",
     "intention_90_day": "Close DBL Partners Fund IV focused on climate and social impact",
     "matching_summary": "Nancy P. leads DBL Partners, the double bottom line VC firm that was early to Tesla, SolarCity, and The Climate Corporation. Proved climate and returns aren't mutually exclusive."},
    {"name": "Carmichael R.", "role": "science", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["sustainable materials", "energy", "carbon removal"], "top_climate_area": "sustainable materials",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Boston",
     "stage": "operator", "superpower": "Materials scientist vetting breakthrough climate technologies for Gates's Breakthrough Energy",
     "intention_90_day": "Identify and fund 3 new breakthrough materials companies via BEV",
     "matching_summary": "Carmichael R. is a managing partner at Breakthrough Energy Ventures, bringing deep materials science expertise to evaluate hard-tech climate investments."},
    {"name": "Emily K.", "role": "gtm", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "energy", "climate finance"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Built the leading accelerator and venture studio for climate tech startups",
     "intention_90_day": "Launch Powerhouse Fund III and graduate 10 new portfolio companies",
     "matching_summary": "Emily K. founded Powerhouse, the venture firm and innovation platform for climate tech. Connector and GTM strategist at the center of the SF climate ecosystem."},
    {"name": "Shayle K.", "role": "gtm", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["energy", "grid infrastructure", "climate finance"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "remote-open", "location": "NYC",
     "stage": "operator", "superpower": "Top climate tech analyst turned podcast host turned investor",
     "intention_90_day": "Deploy Energy Impact Partners fund into grid modernization startups",
     "matching_summary": "Shayle K. is a partner at Energy Impact Partners and host of the Catalyst podcast. Deep analytical expertise in energy markets and grid infrastructure investing."},
    {"name": "Dawn L.", "role": "ops", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["energy", "ocean", "climate finance"], "top_climate_area": "energy",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "operator", "superpower": "Runs the premier climate tech accelerator connecting startups to utility and corporate partners",
     "intention_90_day": "Scale Elemental Excelerator's deployment fund to bridge the climate tech valley of death",
     "matching_summary": "Dawn L. leads Elemental Excelerator, which funds and deploys climate technologies in partnership with utilities and governments. Operations leader bridging startups and incumbents."},
    # --- Climate philanthropy from tech ---
    {"name": "Bill G.", "role": "science", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["energy", "carbon removal", "hydrogen", "sustainable materials"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Seattle",
     "stage": "operator", "superpower": "Microsoft founder deploying billions to solve the hardest climate problems",
     "intention_90_day": "Advance Breakthrough Energy Catalyst projects in green hydrogen and long-duration storage",
     "matching_summary": "Bill G. founded Breakthrough Energy to fund the technologies needed to reach net zero. Backs the hardest problems — steel, cement, aviation fuel — where market incentives alone won't work."},
    {"name": "Laurene P.", "role": "policy", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["food", "agriculture", "biodiversity", "policy"], "top_climate_area": "food",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "operator", "superpower": "Emerson Collective founder investing at the intersection of climate, education, and social justice",
     "intention_90_day": "Launch regenerative agriculture fund through Emerson Collective",
     "matching_summary": "Laurene P. leads Emerson Collective, investing in climate solutions that also address social equity. Focused on food systems, regenerative agriculture, and climate policy."},
    {"name": "Jeff B.", "role": "ops", "role_needed": "science", "lane": "idea",
     "climate_areas": ["energy", "biodiversity", "carbon removal", "climate finance"], "top_climate_area": "biodiversity",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Seattle",
     "stage": "operator", "superpower": "Deploying $10B Earth Fund to accelerate nature-based and technology solutions",
     "intention_90_day": "Announce next round of Bezos Earth Fund grants for tropical forest conservation",
     "matching_summary": "Jeff B. launched the $10B Bezos Earth Fund, one of the largest climate philanthropic commitments. Focused on biodiversity, landscape restoration, and climate justice."},
    {"name": "Marc B.", "role": "product", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["forestry", "biodiversity", "ocean"], "top_climate_area": "forestry",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "operator", "superpower": "Salesforce founder championing corporate climate action and trillion-tree reforestation",
     "intention_90_day": "Hit 50M trees planted through 1t.org corporate partnerships",
     "matching_summary": "Marc B. leads Salesforce's net-zero push and co-founded 1t.org to plant a trillion trees. Product thinker applying platform scale to corporate climate commitments."},
    {"name": "Michael B.", "role": "policy", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["policy", "energy", "buildings"], "top_climate_area": "policy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "NYC",
     "stage": "operator", "superpower": "Deploying billions through Bloomberg Philanthropies to shut down coal and electrify cities",
     "intention_90_day": "Expand Beyond Coal campaign to accelerate coal retirement in Southeast Asia",
     "matching_summary": "Michael B. has spent over $1B through Bloomberg Philanthropies on climate, from the Beyond Coal campaign to city-level electrification. Policy leader seeking engineering innovation to fund."},
    # --- Climate researchers / operators from tech ---
    {"name": "Ramez N.", "role": "science", "role_needed": "product", "lane": "flexible",
     "climate_areas": ["solar", "wind", "energy", "grid infrastructure"], "top_climate_area": "solar",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Seattle",
     "stage": "researcher", "superpower": "Ex-Microsoft futurist who wrote the definitive analysis of clean energy cost curves",
     "intention_90_day": "Publish updated solar + storage learning curve projections through 2040",
     "matching_summary": "Ramez N. is an energy futurist and ex-Microsoft exec who authored the influential analyses showing solar and wind will be cheapest energy ever. Science communicator seeking product-minded collaborators."},
    {"name": "Arun M.", "role": "science", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["energy", "hydrogen", "grid infrastructure"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "SF",
     "stage": "researcher", "superpower": "Founded ARPA-E, led Google energy, now dean of Stanford's climate school",
     "intention_90_day": "Launch Stanford Doerr School's industry partnership program for clean energy R&D",
     "matching_summary": "Arun M. has led climate innovation from ARPA-E to Google to Stanford. Deep expertise in energy systems, hydrogen, and translating research into commercial reality."},
    {"name": "Julio F.", "role": "science", "role_needed": "gtm", "lane": "flexible",
     "climate_areas": ["carbon removal", "hydrogen", "policy"], "top_climate_area": "carbon removal",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "operator", "superpower": "Leading carbon management scientist bridging policy, technology, and investment",
     "intention_90_day": "Publish Carbon Direct's annual state of carbon removal report",
     "matching_summary": "Julio F. leads Carbon Direct, advising companies and governments on carbon management strategy. Former DOE official with deep expertise in CCS and carbon removal pathways."},
    {"name": "Jason J.", "role": "gtm", "role_needed": "product", "lane": "flexible",
     "climate_areas": ["energy", "climate finance", "carbon removal"], "top_climate_area": "climate finance",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Boston",
     "stage": "repeat-founder", "superpower": "Built the largest climate tech media and community platform",
     "intention_90_day": "Scale MCJ Collective fund to $200M AUM",
     "matching_summary": "Jason J. founded My Climate Journey, the podcast and community that became the connective tissue of climate tech. Now deploying capital through MCJ Collective ventures."},
    {"name": "Katherine H.", "role": "policy", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["grid infrastructure", "energy", "policy"], "top_climate_area": "grid infrastructure",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "operator", "superpower": "Top energy policy strategist connecting grid innovation to regulatory change",
     "intention_90_day": "Advance grid interconnection reform at FERC to unblock 2 TW of clean energy projects",
     "matching_summary": "Katherine H. leads 38 North Solutions, advising on clean energy policy and grid modernization. Deep expertise in the regulatory landscape that determines which climate technologies succeed."},
    {"name": "Jesse J.", "role": "science", "role_needed": "policy", "lane": "flexible",
     "climate_areas": ["energy", "grid infrastructure", "wind", "solar"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "NYC",
     "stage": "researcher", "superpower": "Princeton energy systems modeler shaping US decarbonization pathways",
     "intention_90_day": "Release updated REPEAT Project analysis of IRA implementation progress",
     "matching_summary": "Jesse J. runs Princeton's ZERO Lab, modeling the fastest paths to decarbonize the US energy system. His REPEAT Project tracks real-world impact of climate legislation."},
    {"name": "Jessika T.", "role": "science", "role_needed": "product", "lane": "flexible",
     "climate_areas": ["solar", "wind", "EVs", "energy"], "top_climate_area": "solar",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Boston",
     "stage": "researcher", "superpower": "MIT professor who quantifies technology learning curves to predict clean energy costs",
     "intention_90_day": "Publish new framework for predicting which clean technologies will reach cost parity fastest",
     "matching_summary": "Jessika T. is an MIT professor studying how clean energy technologies improve and scale. Her learning curve research helps investors and policymakers pick winners."},
    # --- Additional climate tech founders ---
    {"name": "Audrey Z.", "role": "ops", "role_needed": "engineering", "lane": "flexible",
     "climate_areas": ["grid infrastructure", "energy"], "top_climate_area": "grid infrastructure",
     "commitment": "full-time", "arrangement": "remote-open", "location": "SF",
     "stage": "operator", "superpower": "Led grid transformation in Australia, then brought AI to energy at Google X",
     "intention_90_day": "Deploy AI-driven grid optimization for 3 new utility partners",
     "matching_summary": "Audrey Z. ran the Australian Energy Market Operator and led energy projects at X (Google). Operations leader applying AI and software to modernize the electric grid."},
    {"name": "Sunil P.", "role": "product", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["transport", "EVs", "energy"], "top_climate_area": "transport",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Three-time founder bridging ride-sharing and clean transportation",
     "intention_90_day": "Launch fleet electrification platform for ride-share and delivery companies",
     "matching_summary": "Sunil P. co-founded Spring Health and was an early advocate for combining ride-sharing with EV adoption. Serial product innovator in clean transportation."},
    {"name": "Bruce U.", "role": "gtm", "role_needed": "science", "lane": "flexible",
     "climate_areas": ["climate finance", "energy", "carbon removal"], "top_climate_area": "climate finance",
     "commitment": "exploring", "arrangement": "remote-open", "location": "NYC",
     "stage": "operator", "superpower": "Columbia Business School professor teaching the next generation of climate investors",
     "intention_90_day": "Publish updated climate finance case studies for MBA curriculum",
     "matching_summary": "Bruce U. teaches climate finance at Columbia Business School and advises institutional investors on clean energy transitions. Bridges academia and Wall Street."},
    {"name": "Nat K.", "role": "gtm", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "climate finance"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Pioneered consumer solar financing that made rooftop solar affordable for homeowners",
     "intention_90_day": "Scale new solar lending product to 100K households",
     "matching_summary": "Nat K. founded Clean Power Finance (now Spruce), creating the financing tools that made residential solar mainstream. GTM strategist seeking engineering talent."},
    {"name": "Will W.", "role": "product", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "buildings", "energy"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Austin",
     "stage": "first-time-founder", "superpower": "Built vertically integrated home solar platform simplifying the install process",
     "intention_90_day": "Launch home battery + solar bundled offering in 5 new states",
     "matching_summary": "Will W. founded Palmetto, the end-to-end platform for home solar adoption. Product leader focused on making clean energy as easy as signing up for a streaming service."},
    {"name": "David B.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["solar", "sustainable materials"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "repeat-founder", "superpower": "Led SunPower's high-efficiency solar cell engineering for two decades",
     "intention_90_day": "Prototype next-gen perovskite-silicon tandem solar cell at commercial efficiency",
     "matching_summary": "David B. is a veteran solar engineer from SunPower, focused on pushing photovoltaic efficiency limits. Deep hardware expertise seeking GTM help to commercialize next-gen cells."},
    {"name": "Mike B.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["circular economy", "sustainable materials"], "top_climate_area": "circular economy",
     "commitment": "full-time", "arrangement": "remote-open", "location": "SF",
     "stage": "repeat-founder", "superpower": "Invented industrial-scale process for recycling any plastic back to raw material",
     "intention_90_day": "Open first automated plastics sorting and recycling mega-facility",
     "matching_summary": "Mike B. founded MBA Polymers, pioneering the technology to recycle mixed plastics at industrial scale. Engineer seeking GTM help to license technology globally."},
    {"name": "Ellen W.", "role": "science", "role_needed": "ops", "lane": "flexible",
     "climate_areas": ["energy", "grid infrastructure", "hydrogen"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Boston",
     "stage": "researcher", "superpower": "Former ARPA-E director who shaped the US clean energy research agenda",
     "intention_90_day": "Advise 3 new energy startups spinning out of national labs",
     "matching_summary": "Ellen W. directed ARPA-E, funding breakthrough energy research from fusion to grid storage. Deep science background bridging national labs and commercialization."},
    # --- More climate tech operators/founders ---
    {"name": "Abe G.", "role": "product", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["food", "agriculture", "water"], "top_climate_area": "food",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "first-time-founder", "superpower": "Building the data platform for regenerative agriculture measurement and verification",
     "intention_90_day": "Onboard 50 farms to soil carbon measurement platform",
     "matching_summary": "Abe G. is building tools to measure and verify soil carbon in regenerative farming. Product leader seeking engineering depth for satellite and sensor data pipelines."},
    {"name": "Lisa D.", "role": "engineering", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["wind", "ocean", "energy"], "top_climate_area": "wind",
     "commitment": "full-time", "arrangement": "colocated", "location": "Boston",
     "stage": "first-time-founder", "superpower": "Designing next-gen floating offshore wind platforms for deep water deployment",
     "intention_90_day": "Complete 1:10 scale prototype testing for floating wind turbine foundation",
     "matching_summary": "Lisa D. is an ocean engineer building floating platforms to unlock offshore wind in deep waters where fixed foundations can't reach. Seeking GTM help for utility partnerships."},
    {"name": "Carlos M.", "role": "engineering", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["hydrogen", "energy", "transport"], "top_climate_area": "hydrogen",
     "commitment": "full-time", "arrangement": "colocated", "location": "Denver",
     "stage": "first-time-founder", "superpower": "Building modular green hydrogen electrolyzers at a fraction of current costs",
     "intention_90_day": "Ship first commercial electrolyzer units to industrial hydrogen buyers",
     "matching_summary": "Carlos M. is developing low-cost modular electrolyzers to make green hydrogen competitive with natural gas. Hardware engineer seeking operations leadership to scale manufacturing."},
    {"name": "Sarah C.", "role": "policy", "role_needed": "product", "lane": "flexible",
     "climate_areas": ["policy", "climate finance", "energy"], "top_climate_area": "policy",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "operator", "superpower": "Former White House climate advisor connecting policy levers to market opportunities",
     "intention_90_day": "Help 10 climate startups navigate IRA tax credit qualification",
     "matching_summary": "Sarah C. advised on climate policy at the White House and now helps climate companies capture policy incentives. Deep expertise in translating regulations into business strategy."},
    {"name": "Maya T.", "role": "science", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["agriculture", "food", "biodiversity"], "top_climate_area": "agriculture",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Austin",
     "stage": "first-time-founder", "superpower": "Developing microbial solutions to replace synthetic fertilizers",
     "intention_90_day": "Complete field trials showing 30% fertilizer reduction with equivalent crop yields",
     "matching_summary": "Maya T. is a microbiologist engineering soil microbes to fix nitrogen naturally, replacing synthetic fertilizers. Seeking an engineering cofounder to build the fermentation and delivery system."},
    {"name": "Kevin C.", "role": "engineering", "role_needed": "product", "lane": "joiner",
     "climate_areas": ["buildings", "energy", "grid infrastructure"], "top_climate_area": "buildings",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "operator", "superpower": "Led building decarbonization engineering at a major HVAC manufacturer",
     "intention_90_day": "Deploy heat pump retrofit solution in 500 NYC apartment units",
     "matching_summary": "Kevin C. is a mechanical engineer focused on electrifying building heating. Deep expertise in heat pump systems and building energy retrofits at scale."},
    {"name": "Rachel K.", "role": "gtm", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["circular economy", "food", "sustainable materials"], "top_climate_area": "circular economy",
     "commitment": "full-time", "arrangement": "colocated", "location": "LA",
     "stage": "first-time-founder", "superpower": "Building the marketplace connecting food waste generators with upcycling manufacturers",
     "intention_90_day": "Sign 20 restaurant chains to food waste diversion program",
     "matching_summary": "Rachel K. is building a platform to turn commercial food waste into valuable products. GTM strategist seeking engineering talent to build supply chain logistics."},
    {"name": "Derek W.", "role": "engineering", "role_needed": "science", "lane": "idea",
     "climate_areas": ["carbon removal", "ocean"], "top_climate_area": "ocean",
     "commitment": "full-time", "arrangement": "colocated", "location": "SF",
     "stage": "first-time-founder", "superpower": "Developing ocean alkalinity enhancement to sequester gigatons of CO2",
     "intention_90_day": "Complete first open-ocean alkalinity enhancement pilot with MRV verification",
     "matching_summary": "Derek W. is building ocean-based carbon removal through alkalinity enhancement. Engineer seeking ocean chemistry expertise to validate and scale the approach."},
    {"name": "Tina H.", "role": "ops", "role_needed": "engineering", "lane": "joiner",
     "climate_areas": ["EVs", "transport", "grid infrastructure"], "top_climate_area": "EVs",
     "commitment": "full-time", "arrangement": "colocated", "location": "LA",
     "stage": "operator", "superpower": "Scaled EV charging operations from 100 to 10,000 stations across the US",
     "intention_90_day": "Launch vehicle-to-grid pilot program with 3 fleet operators",
     "matching_summary": "Tina H. is an EV infrastructure operations leader who built and scaled charging networks. Seeking engineering talent to build vehicle-to-grid bidirectional charging systems."},
    {"name": "Omar F.", "role": "science", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["solar", "sustainable materials", "energy"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "colocated", "location": "Boston",
     "stage": "researcher", "superpower": "MIT perovskite solar researcher pushing toward 35% efficiency tandem cells",
     "intention_90_day": "Spin out perovskite-silicon tandem cell startup from MIT lab",
     "matching_summary": "Omar F. is an MIT researcher pioneering perovskite solar cells that could double efficiency at a fraction of silicon costs. Seeking GTM cofounder to commercialize the technology."},
    {"name": "Nina P.", "role": "product", "role_needed": "science", "lane": "idea",
     "climate_areas": ["water", "agriculture", "food"], "top_climate_area": "water",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Denver",
     "stage": "first-time-founder", "superpower": "Building precision irrigation platform using satellite and soil sensor data",
     "intention_90_day": "Launch pilot with 10 large-scale farms in California's Central Valley",
     "matching_summary": "Nina P. is building smart irrigation tools that cut agricultural water use by 40% using real-time satellite and sensor data. Product leader seeking agri-science expertise."},
    {"name": "James L.", "role": "engineering", "role_needed": "ops", "lane": "idea",
     "climate_areas": ["grid infrastructure", "energy", "wind"], "top_climate_area": "grid infrastructure",
     "commitment": "full-time", "arrangement": "colocated", "location": "Austin",
     "stage": "first-time-founder", "superpower": "Building software to cut grid interconnection timelines from years to months",
     "intention_90_day": "Onboard 5 utilities onto automated interconnection study platform",
     "matching_summary": "James L. is building software to accelerate the grid interconnection queue, where 2+ TW of clean energy projects are stuck waiting. Engineer seeking ops leader to manage utility relationships."},
    {"name": "Fatima A.", "role": "science", "role_needed": "product", "lane": "idea",
     "climate_areas": ["hydrogen", "carbon removal", "sustainable materials"], "top_climate_area": "hydrogen",
     "commitment": "full-time", "arrangement": "colocated", "location": "Chicago",
     "stage": "researcher", "superpower": "Catalysis researcher developing novel catalysts for green hydrogen production",
     "intention_90_day": "Demonstrate 2x improvement in electrolyzer catalyst efficiency at pilot scale",
     "matching_summary": "Fatima A. is a catalysis researcher developing breakthrough materials for cheaper green hydrogen production. Seeking a product cofounder to translate lab results into a startup."},
    {"name": "Raj V.", "role": "product", "role_needed": "engineering", "lane": "joiner",
     "climate_areas": ["climate finance", "energy", "carbon removal"], "top_climate_area": "climate finance",
     "commitment": "full-time", "arrangement": "colocated", "location": "NYC",
     "stage": "operator", "superpower": "Ex-Goldman climate finance product leader building tools for carbon credit markets",
     "intention_90_day": "Ship carbon credit verification platform for voluntary market buyers",
     "matching_summary": "Raj V. left Goldman Sachs to build fintech tools for carbon markets. Product expert bringing institutional finance rigor to voluntary carbon credit trading."},
    # --- Historic / iconic climate figures ---
    {"name": "Albert E.", "role": "science", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["energy", "hydrogen", "grid infrastructure"], "top_climate_area": "energy",
     "commitment": "exploring", "arrangement": "remote-open", "location": "Boston",
     "stage": "researcher", "superpower": "Mass-energy equivalence theorist with strong opinions about the photoelectric effect",
     "intention_90_day": "Publish unified field theory of clean energy transition",
     "matching_summary": "Albert E. is a theoretical physicist who believes imagination is more important than knowledge. Interested in converting his famous equation into practical fusion energy."},
    {"name": "Jimmy C.", "role": "policy", "role_needed": "engineering", "lane": "idea",
     "climate_areas": ["solar", "buildings", "policy"], "top_climate_area": "solar",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Austin",
     "stage": "operator", "superpower": "Put solar panels on the White House before it was cool",
     "intention_90_day": "Build 500 energy-efficient homes in underserved communities",
     "matching_summary": "Jimmy C. is a former executive who pioneered rooftop solar adoption at the highest levels of government. Now focused on affordable housing and building electrification."},
    {"name": "Rachel C.", "role": "science", "role_needed": "gtm", "lane": "idea",
     "climate_areas": ["biodiversity", "ocean", "agriculture", "policy"], "top_climate_area": "biodiversity",
     "commitment": "full-time", "arrangement": "remote-open", "location": "Boston",
     "stage": "researcher", "superpower": "Marine biologist whose writing launched the modern environmental movement",
     "intention_90_day": "Publish landmark study on pesticide impact on pollinator ecosystems",
     "matching_summary": "Rachel C. is a marine biologist and science communicator who proved that rigorous research paired with compelling storytelling can change the world. Seeking GTM help to scale impact."},
    {"name": "Al G.", "role": "gtm", "role_needed": "science", "lane": "idea",
     "climate_areas": ["climate finance", "policy", "energy", "carbon removal"], "top_climate_area": "climate finance",
     "commitment": "full-time", "arrangement": "remote-open", "location": "SF",
     "stage": "repeat-founder", "superpower": "Oscar-winning climate communicator who made inconvenient truths mainstream",
     "intention_90_day": "Close Generation Investment Management's next sustainable equity fund",
     "matching_summary": "Al G. is the climate communicator who brought global warming to mainstream awareness and co-founded Generation Investment Management. GTM leader seeking deep science partnerships to invest in."},
    {"name": "Jay I.", "role": "policy", "role_needed": "product", "lane": "idea",
     "climate_areas": ["energy", "policy", "grid infrastructure", "buildings"], "top_climate_area": "policy",
     "commitment": "full-time", "arrangement": "colocated", "location": "Seattle",
     "stage": "operator", "superpower": "Ran for president on an all-climate platform, then passed the most ambitious state clean energy laws",
     "intention_90_day": "Advise 5 states on replicating Washington's clean energy standard",
     "matching_summary": "Jay I. is the policy leader who proved climate can be a winning political platform. Passed landmark clean energy legislation and now advises on state-level climate policy replication."},
]
# fmt: on

CLIMATE_AREAS = [
    "energy",
    "transport",
    "buildings",
    "food",
    "water",
    "carbon removal",
    "biodiversity",
    "circular economy",
    "climate finance",
    "policy",
    "grid infrastructure",
    "EVs",
    "solar",
    "wind",
    "hydrogen",
    "sustainable materials",
    "agriculture",
    "ocean",
    "forestry",
]


FILLER_FIRST_NAMES = [
    "Ada",
    "Ben",
    "Cara",
    "Dan",
    "Eve",
    "Finn",
    "Grace",
    "Hank",
    "Iris",
    "Jack",
    "Kate",
    "Leo",
    "Mia",
    "Nate",
    "Olive",
    "Pete",
    "Quinn",
    "Rosa",
    "Sam",
    "Tara",
    "Uri",
    "Vera",
    "Wade",
    "Xena",
    "Yuki",
    "Zane",
]

ROLES = ["engineering", "product", "gtm", "science", "ops", "policy"]
LANES = ["idea", "joiner", "flexible"]
COMMITMENTS = ["full-time", "exploring"]
ARRANGEMENTS = ["colocated", "remote-open"]
LOCATIONS = ["SF", "NYC", "Boston", "Austin", "LA", "Seattle", "Denver", "Chicago"]
STAGES = ["first-time-founder", "repeat-founder", "operator", "researcher"]


def _generate_random_filler(count: int) -> list[dict]:
    """Generate random filler attendees when more are needed than curated people."""
    fillers = []
    for i in range(count):
        first = FILLER_FIRST_NAMES[i % len(FILLER_FIRST_NAMES)]
        last_initial = chr(65 + (i // len(FILLER_FIRST_NAMES)) % 26)
        areas = random.sample(CLIMATE_AREAS, k=random.randint(1, 4))
        role = random.choice(ROLES)
        other_roles = [r for r in ROLES if r != role]
        fillers.append(
            {
                "name": f"{first} {last_initial}.",
                "role": role,
                "role_needed": random.choice(other_roles),
                "lane": random.choice(LANES),
                "climate_areas": areas,
                "top_climate_area": areas[0],
                "commitment": random.choice(COMMITMENTS),
                "arrangement": random.choice(ARRANGEMENTS),
                "location": random.choice(LOCATIONS),
                "stage": random.choice(STAGES),
                "superpower": f"Experienced {role} professional in {areas[0]}",
                "intention_90_day": f"Explore opportunities in {areas[0]}",
                "matching_summary": f"{first} {last_initial}. is a {role} professional focused on {areas[0]}.",
            }
        )
    return fillers


def generate_attendees(count: int = 60) -> list[dict]:
    people = PEOPLE[:]
    random.shuffle(people)
    selected = people[:count]

    if count > len(people):
        selected.extend(_generate_random_filler(count - len(people)))

    attendees = []
    for person in selected:
        first_name = person["name"].split()[0]
        attendee = {
            "id": str(uuid.uuid4())[:8],
            "name": person["name"],
            "email": f"{first_name.lower()}@test.com",
            "location": person["location"],
            "linkedin_url": "",
            "token": str(uuid.uuid4())[:8],
            "lane": person["lane"],
            "role": person["role"],
            "role_needed": person["role_needed"],
            "climate_areas": person["climate_areas"],
            "top_climate_area": person["top_climate_area"],
            "commitment": person["commitment"],
            "arrangement": person["arrangement"],
            "proof_link_1": "",
            "proof_link_2": "",
            "intention_90_day": person["intention_90_day"],
            "domain_tags": person["climate_areas"][:2],
            "technical_depth": random.randint(1, 5),
            "stage": person["stage"],
            "superpower": person["superpower"],
            "matching_summary": person["matching_summary"],
            "red_flags": [],
            "status": "not-arrived",
            "source": "application",
            "has_full_scoring": True,
            "pit_stop_count": 0,
        }
        attendees.append(attendee)

    return attendees


def generate_matrix(attendees: list[dict]) -> dict[str, dict]:
    """Generate realistic-ish compatibility scores for all pairs."""
    matrix = {}

    for a, b in combinations(attendees, 2):
        pair_key = ":".join(sorted([a["id"], b["id"]]))

        # Base score — random but influenced by compatibility signals
        base = random.randint(25, 75)

        # Bonus for complementary roles
        if a["role"] != b["role"] and a["role_needed"] == b["role"]:
            base += random.randint(5, 15)
        if b["role_needed"] == a["role"]:
            base += random.randint(5, 10)

        # Bonus for lane complementarity
        if (a["lane"] == "idea" and b["lane"] == "joiner") or (
            a["lane"] == "joiner" and b["lane"] == "idea"
        ):
            base += random.randint(5, 10)

        # Bonus for climate overlap
        overlap = len(set(a["climate_areas"]) & set(b["climate_areas"]))
        base += overlap * random.randint(2, 5)

        # Top area match
        if a["top_climate_area"] == b["top_climate_area"]:
            base += random.randint(5, 10)

        # Penalty for incompatible arrangements
        if (
            a["arrangement"] == "colocated"
            and b["arrangement"] == "colocated"
            and a["location"] != b["location"]
        ):
            base -= 30

        score = max(1, min(100, base))

        climate_topics = list(set(a["climate_areas"]) & set(b["climate_areas"]))
        spark_topic = climate_topics[0] if climate_topics else a["top_climate_area"]

        matrix[pair_key] = {
            "score": score,
            "rationale": f"{'Strong' if score > 70 else 'Moderate' if score > 45 else 'Weak'} match based on {a['role']}/{b['role']} complementarity and {spark_topic} overlap.",
            "spark": f"Discuss approaches to {spark_topic} and potential co-founding synergies.",
        }

    return matrix


def generate_walkup_badges(count: int = 20) -> list[dict]:
    """Generate walk-up reserve badges with fun slugs."""
    adjectives = [
        "Pink",
        "Turquoise",
        "Golden",
        "Silver",
        "Cosmic",
        "Crimson",
        "Emerald",
        "Amber",
        "Sapphire",
        "Coral",
        "Indigo",
        "Scarlet",
        "Azure",
        "Violet",
        "Copper",
        "Jade",
        "Ruby",
        "Onyx",
        "Pearl",
        "Topaz",
    ]
    animals = [
        "Unicorn",
        "Armadillo",
        "Falcon",
        "Otter",
        "Phoenix",
        "Dolphin",
        "Panther",
        "Penguin",
        "Lynx",
        "Hummingbird",
        "Chameleon",
        "Fox",
        "Hawk",
        "Koala",
        "Narwhal",
        "Raven",
        "Toucan",
        "Wolf",
        "Zebra",
        "Crane",
    ]

    badges = []
    random.shuffle(adjectives)
    random.shuffle(animals)

    for i in range(min(count, len(adjectives))):
        slug = f"{adjectives[i]} {animals[i]}"
        badges.append(
            {
                "slug": slug,
                "token": str(uuid.uuid4())[:8],
            }
        )

    return badges


def seed(
    attendee_count: int = 60,
    output_dir: str = "data",
) -> None:
    """Generate all test data files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Generating {attendee_count} attendees...")
    attendees = generate_attendees(attendee_count)
    with open(out / "enriched_attendees.json", "w") as f:
        json.dump(attendees, f, indent=2)
    print(f"  → {out / 'enriched_attendees.json'}")

    pair_count = attendee_count * (attendee_count - 1) // 2
    print(f"Generating {pair_count} pair scores...")
    matrix = generate_matrix(attendees)
    with open(out / "matrix.json", "w") as f:
        json.dump(matrix, f, indent=2)
    print(f"  → {out / 'matrix.json'}")

    print("Generating 20 walk-up badges...")
    badges = generate_walkup_badges(20)
    with open(out / "walkup_badges.json", "w") as f:
        json.dump(badges, f, indent=2)
    print(f"  → {out / 'walkup_badges.json'}")

    print("Done!")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed(attendee_count=count)


if __name__ == "__main__":
    main()
