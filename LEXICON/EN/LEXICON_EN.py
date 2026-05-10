# LEXICON\EN\LEXICON_EN.py
from LEXICON.EN.LEXICON_handlers_en import LEXICON_HANDLERS_EN

LEXICON_EN ={
# Participant status names
    "user_status": {
        "all members": "👥 All Members",
        "admin": "🛡️ Administrator",
        "registrator": "📝 Registrator",
        "superregistrator": "⚡ Super-Registrator",
        "moderator": "⚖️ Moderator",
        "delegate": "🗳️ Delegate",
        "proxy": "🤝 Representative",
        "candidate": "🌱 Candidate",
        "member": "✅ Member",
        "user": "👤 User",
        "owner": "👑 Owner",
        "votist": "🗳️ Voter",
        "pre-registrator": "🌟 Registrator Candidate",
    },

    # Voting status names
    "voting_status": {
        "add_variants": "📝 Variant Submission Phase",
        "ongoing": "🔄 In Progress",
        "confirmation": "✅ Results Confirmation",
        "completed": "🏁 Completed",
    },

    # Variant status names
    "variant_status": {
        "valid": "✔️ Valid",
        "invalid": "❌ Removed",
        "loser": "🔻 Not Selected",
        "winner": "🏆 Winner",
    },

    # Titles in variant list
    "status_title_map": {
        "valid": "✅ Valid Variants",
        "winner": "🏆 Winning Variants",
        "loser": "🔻 Variants Not Selected",
        "invalid": "❌ Removed Variants",
    },

    # Status assignment buttons
    "AppointAs_admin": "🛡️ Appoint as Administrator",
    "AppointAs_registrator": "📝 Appoint as Registrator",
    "AppointAs_moderator": "⚖️ Appoint as Moderator",
    "AppointAs_delegate": "🗳️ Appoint as Delegate",
    "AppointAs_proxy": "🤝 Appoint as Representative",
    "AppointAs_member": "✅ Accept into Group",

    # Status removal buttons
    "not_admin": "🚫 Remove from Administrators",
    "not_registrator": "🚫 Remove from Registrators",
    "not_moderator": "🚫 Remove from Moderators",
    "not_delegate": "🚫 Remove from Delegates",
    "not_proxy": "🚫 Remove from Representatives",
    "not_member": "🚫 Remove from Members",
    "not_pre-registrator": "🚫 Remove from Registrator Candidates",

    # Main menu buttons
    "ongoing_votings": "🔄 Ongoing Votings",
    "completed_votings": "🏁 Completed Votings",
    "future_votings": "📅 Upcoming Votings",
    "registration": "📋 Register",
    "new_voting": "➕ Create Voting",
    "new_variant": "📝 Add Variant",
    "new_status": "👤 Change Member Status",
    "new_registrator": "📝 Add Registrator",
    "registrators_list": "📜 Registrators List",
    "new_member": "🌱 Accept New Member",
    "select_proxy": "🤝 Select Representative",
    "select_subproxy": "🔄 Select Alternate",
    "become_proxy": "🤝 Become Representative",
    "resign_from_proxy": "🚪 Resign as Representative",
    "resign_from_registrator": "🚪 Resign as Registrator",
    "resign_from_admin": "🚪 Resign as Administrator",
    "become_registrator": "📝 Become Registrator",
    "main_menu": "🏠 Main Menu",
    "leave_the_group": "👋 Leave Group",
    "admin_bot": "⚙️ Administer Bot",
    "help": "❓ Help",
    "profile": "👤 Profile",
    "info": "ℹ️ Information",
    "list_of_proxy": "📋 Representatives List",
    "tokens": "🔑 Token Management",

    # Secondary menu buttons
    "admin_voting": "⚙️ Manage Voting",
    "voting_start": "▶️ Start Voting",
    "voting_stage": "📊 Interim Results",
    "voting_final": "🏁 Launch Final Phase",
    "confirmation_of_voting_results": "✅ Start Results Approval",
    "confirmation_of_voting_results_stop": "🛑 Stop Results Approval",
    "voting_complete": "🔚 Complete Voting",
    "select_variant": "🎯 Select Voting Variant",
    "delete variant": "🗑️ Delete Variant",
    "show_oll_variants": "📋 Show All Variants",
    "continue_voting": "▶️ Continue Voting",
    "show_variants": "👀 View Variants",
    "back_to_votings": "🔙 Back to Votings List",
    "return_to_main_menu": "🏠 Return to Main Menu",
    "create_variant": "➕ Add Variant to This Voting",
    "show_result": "📈 Show Results",
    "reopen": "🔄 Reopen",
    "Vote for this variant": "🗳️ Vote for This Variant",

    # Notification levels
    "max_info": "📢 All Notifications",
    "average_info": "📌 Important Only",
    "min_info": "🔕 Critical Only",

    "edit_club_name": "✏️ Edit Group Name",
    "edit_club_description": "📝 Edit Description",
    "edit_club_conditions": "📜 Edit Participation Rules",
    "add_channel": "➕ Add Channel or Chat",
    "remove_channel": "🗑️ Remove Channel",
    "set_main_channel": "🎯 Set Main Channel",
    "set_stage_durations": "⏱️ Set Stage Durations",
    "set_threshold": "📊 Set Delegate Threshold",

    "edit_username": "👤 Display Name / Alias",
    "edit_description": "📝 About Me",
    "change_info_level": "🔔 Notification Level",

    "club_info": "🏢 About the Group",
    "bot_info": "🤖 About the Bot",
    "status_info": "🏷️ Roles & Statuses",
    "proxy_list": "🤝 Representatives List",
    "voting_info": "🗳️ How Voting Works",
    "about": "❓ What is this Bot for?",
    "proxy_info": "ℹ️ About the Representative Role",

    "admin_members": "👥 Manage Members",
    "export_members": "📤 Export Members List",
    "ban_member": "🚫 Ban Member",
    "unban_member": "✅ Unban Member",

    "mailing_list": "📬 Broadcasts",
    "mailing_all": "📢 Send to All",
    "mailing_members": "👥 Send to Members",
    "mailing_user": "💬 Direct Message",
    "mailing_followers": "📩 Send to Followers",

    "enter_token": "🔑 Enter Token",
    "request_token": "📝 Request Token",

    "Don't make any decision": "🤷 Abstain / No Decision",
    "An error occurred, please try again": "❌ An error occurred. Please try again.",
    "info_menu": "📚 Choose what you'd like to learn more about:",

        # Profile information
    "profile_info": ("🆔 ID: {id}\n"
            "👤 First Name: {first_name}\n"
            "📛 Last Name: {last_name}\n"
            "✏️ Alias: {username}\n"
            "📝 About: {description}\n"
            "🔔 Notification Level: {info_level}\n"
            "🔑 Token: {token}\n"
            "🤝 Representative/Alternate: {proxy_username}\n"
            ),
    "your_profile_data": '📋 Your Profile Data:\n',
    "profile_menu": "\n✏️ Select what you'd like to update in your profile",
    "not specified": "📭 Not specified",

    "registration_message": """Please tell us about yourself and why you'd like to join the group.\n
This information will be forwarded to your selected Registrator, who will decide whether to approve your membership.""",

    "reg_cancel_info": """If you wish to continue the registration process — please reply with a message.
If you'd like to cancel — type or tap /cancel""",

    # Bot help text
    "bot_info_text": """
<b>📝 About the Bot</b>

<i>Description</i>
This Telegram bot is designed for collective decision-making through voting and voice delegation. It enables group members to participate in governance, create votings, select representatives, and track results.

<b>📋 Key Features:</b>
• <u>Voting:</u>
  - Members can vote for decision variants
  - If a member doesn't vote, their voice is delegated to their Representative
  - Ability to change your vote before the voting ends

• <u>Voice Delegation:</u>
  - Any member can select a Representative or become one
  - Representatives commit to always casting their vote

<b>👥 Participant Roles:</b>
• User – Member without a special status
• Candidate – Applicant for membership
• Member – Full-fledged participant
• Owner – Group Owner
• Admin – Administrator
• Proxy – Representative
• Delegate – Advanced Representative with extended rights
• Registrator – Membership approval manager

<b>🗳️ Voting Stages:</b>
1. Voting Creation
2. Variant Submission
3. Active Voting
4. Intermediate Rounds (eliminating less popular variants)
5. Final Round (choice between two top variants)
6. Results Confirmation

<b>📊 Statistics & History:</b>
The bot preserves voting history and results for analysis and transparency.

<b>📄 License:</b>
This project is distributed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache License 2.0</a>.
You are free to use, modify, and distribute the code with attribution to the original source.
Commercial use does not require you to open-source your product.
You may create derivative works based on this code (e.g., your own Telegram voting bot).

<b>💻 Source Code:</b>
<a href="https://github.com/Almaz49/CityVote">GitHub Repository</a>

<b>🚀 Getting Started:</b>
1. Register as a participant
2. Get approval from an Admin or Registrator
3. Start voting or delegate your voice

<b>🛠️ Support:</b>
• GitHub Issues: <a href="https://github.com/Almaz49/CityVote/issues">Issues</a>
• Telegram: @CityVote

<b>⚠️ Usage Rules:</b>
• Do not use the bot for spam or abuse
• Respect the rights of other group members
• Follow group rules during votings

<b>🙏 Acknowledgements:</b>
Thank you for using our bot! We hope it helps you make more effective and democratic decisions.
""",

    # Theory about the voting bot
    "about_text": """
<b>🤔 Why Do We Need This Telegram Bot?</b>

The Internet has become an integral part of our lives, removing barriers between people. We can communicate with friends thousands of kilometers away and find like-minded individuals around the globe. Naturally, the Internet should also play a role in improving such an institution as collective democratic decision-making.

<i><b>⚠️ Problems with Traditional Voting Systems:</b></i>
• 🧩 Primitive Mechanisms: Polls often limit themselves to simple questions without accounting for the complexity of decisions.
• ❓ Participant Uncertainty: It's unclear who has voting rights and who doesn't.
• 📉 Low Engagement: Most participants ignore the majority of votings.
• 🗑️ Spam & Chaos: A hyperactive minority overloads the agenda with new votings.
• 🎭 Manipulations: Unsuitable decision variants are added to votings intentionally.
• 🔗 Detached Representatives: Elected representatives stop caring about their constituents' opinions.

<i><b>✅ How CityVote Solves These Problems:</b></i>
• 🔄 Staged Voting Process: The process is divided into stages (creation, variant submission, voting, confirmation), minimizing manipulation risks.
• 🔐 Access Control: Registrators determine who can be a group member and have voting rights.
• 🤝 Voice Delegation: Participants who don't vote personally must select a Representative whose vote will be counted on their behalf.
• 🎯 Limited Voting Creation: Only Delegates who have earned the trust of a sufficient number of participants can create new votings.
• 💡 Flexible Variants: Delegates can add necessary decision variants, and participants can vote to reject a decision entirely.
• 👁️ Continuous Oversight: Representatives remain accountable to their constituents, who can change their choice at any time.

<i><b>🌟 System Advantages:</b></i>
• 🗳️ Every Voice Counts: Even minor issues are resolved considering the majority's opinion.
• 🛡️ Minimized Distortions: The system reduces the risk of manipulations and spam.
• ⚙️ Flexibility: Ability to adapt the system to any community.
• 🌍 Wide Applicability: The bot can be used in condominiums, cooperatives, trade unions, and other communities.

<i><b>💼 Practical Benefits:</b></i>
The "Voting Bot" doesn't replace formal decision-making procedures, but helps develop a consolidated position, simplifying further steps.
""",

    "greetings": """
👋 I help participants take part in votings, select representatives, and stay updated on important group events. Here's what you can do with my help:

✅ <b>For All Members:</b>
• 🗳️ Participate in votings
• 🤝 Select or change your representative 👤
• 🌟 Become a representative yourself
• 🔔 Receive notifications about voting results 📊

👥 <b>For Representatives:</b>
• ✋ Vote on behalf of constituents who haven't voted
• 📬 Send broadcasts to your constituents ✉️

🗳️ <b>For Delegates:</b>
• 📝 Create new votings
• ➕ Add decision variants (while submission period is active)

⚙️ <b>For Administrators:</b>
• ⚙️ Manage voting stages
• 📋 Appoint Registrators
• 🔍 Verify new members

🚀 To get started, please complete your registration.

<b>📋 Basic Commands:</b>
• <code>/start</code> — Start working with the bot
• <code>/help</code> — Get help
""",

    # Help Section
    "user_help": "👋 Hello! This is a voting system bot for your group. "
    "To participate in votings "
    "and access other features — "
    "please complete your registration in the group. "
    'To do this, tap the "Register" button and follow the instructions.'
    '\n\nIf you receive a new status, use the "Help" button again for updated guidance.\n\n',

    "candidate_help": "📋 Your application to join the group is currently under review by the administration. "
    "\nIf you don't receive a response for an extended period, please try contacting "
    "the administration through other channels.\n\n",

    "member_help": "✅ You are now a full member of the group. You can view votings and participate in them. "
    "\nYou can also select a Representative or become one yourself."
    "\nTo become a Representative, tap the corresponding button."
    "\n⚠️ Representatives are required to participate in all votings, so please consider carefully "
    "before taking on this responsibility.",

    "proxy_help": "🤝 You are now a Representative. Remember, this is a significant responsibility — you vote not only for yourself but also for those who have entrusted their voice to you. "
    "You can select an Alternate. If you don't cast a vote, your vote will be counted according to your Alternate's choice. "
    "Any group member can serve as your Alternate."
    "\nTo select an Alternate, tap the corresponding button."
    "\nYou will be prompted to either enter the user's Telegram ID or forward their contact to the bot. "
    '⚠️ Please forward the "Telegram contact" (from the app), not a phone contact from your address book, otherwise it won\'t work.'
    "\nYou can find a user's ID via the Telegram desktop app by enabling the appropriate settings. "
    "Or search online for 'how to find Telegram ID'. If this is difficult, forwarding their contact may be the simplest option.\n\n",

    "delegate_help": "🗳️ You are now a Delegate. This status allows you to create votings and add variants to them. "
    "\nTo create a voting, tap the corresponding button (it should appear in your menu) and follow the instructions. "
    '\nInitially, the voting will be in the "Variant Submission" phase. While in this phase, '
    "you and other Delegates can add decision variants. Once the voting is launched and participants begin casting votes, "
    "adding new variants will no longer be possible."
    '\nTo add a variant, go to "Upcoming Votings", select the desired voting. '
    'A "Add Variant" button should appear in the menu below. Then follow the instructions.'
    "\n⚠️ Please use your privileges responsibly — avoid creating an excessive number of votings or variants.\n\n",

    "pre-registrator_help": "🌟 You have been invited to become a Registrator. If you accept, membership applications will be sent to you via the bot, "
    "which you can approve or decline. You may accept this invitation or decline it.",

    "registrator_help": '📝 You have been appointed as a "Registrator". This means membership applications will be sent to you via the bot. '
    'These applications will include the candidate\'s contact details and their "resume". If you believe the candidate meets '
    "the requirements for group membership, tap the confirmation button. If you're unsure — tap the corresponding button and the application will remain "
    "under review by the Group Owner."
    "\nYou may resign from your Registrator duties at any time.",

    "admin_help": "🛡️ Administrator status grants the right to appoint Registrators (those who verify membership eligibility for new participants). "
    "To appoint a Registrator, tap the corresponding button in the main menu. "
    "Appoint as Registrators those who are well-known and trusted by the community."
    "\nYou will be prompted to either enter the user's Telegram ID or forward their contact to the bot. "
    '⚠️ Please forward the "Telegram contact" (from the app), not a phone contact from your address book, otherwise it won\'t work.'
    "\nYou can find a user's ID via the Telegram desktop app by enabling the appropriate settings. "
    "Or search online for 'how to find Telegram ID'. If this is difficult, forwarding their contact may be the simplest option.\n\n"
    'Additionally, depending on group settings, Administrators can manage votings (tap the "Manage Voting" button '
    "which appears when viewing voting variants.)."
    "\nAdministrators can delete votings or their variants (before the voting is launched). This power is intended to correct technical errors, "
    'such as nearly identical votings or variants, and should not be used for "censorship".'
    '\nAdministrators can also "ban" users, which prevents them from becoming Representatives or Delegates.'
    "\n⚙️ Some administrator features are still under development (including banning and deleting votings).",

    "owner_help": "👑 You are the Group Owner. "
    "\nYou can change the status of any group member by assigning new roles or removing existing ones. "
    "The only exception is the Owner status itself — you cannot add new Owners or remove existing ones.",

    "abstract_help": "\n🗳️ If you cast a vote personally, your vote will be counted according to your choice. "
    "\nIf you don't vote, your vote will be counted according to your Representative's choice. "
    "\nYou can change your Representative or become one yourself at any time. "
    "\n⚠️ Please note: votes from participants who are not Representatives and haven't selected one are not counted in votings. "
    "\n❓ Why is this necessary? Experience shows that most group members don't actively participate in group life. "
    "As a result, votings lose broad participation and legitimacy. A hyperactive minority begins to dominate. "
    "But that doesn't necessarily reflect the majority's opinion. "
    "\nAdditionally, the voice delegation system helps identify the most respected community members. "
    'If a Representative gathers enough delegated votes (the "threshold" is defined by group rules), '
    'they become a "Delegate". Delegates gain the right to create new votings and add decision variants. '
    '\nThe ability to revoke or reassign your vote creates an effective system of constituent oversight over their "elected" representatives. '
    '''This addresses a key flaw of representative democracy: "You elected us, and now you're no longer needed". '''
    "\nHowever, if you prefer not to use the delegation system — you can simply always vote personally.\n\n",

}

LEXICON_EN = LEXICON_EN | LEXICON_HANDLERS_EN