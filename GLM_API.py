# -*- coding: utf-8 -*-
import json

import streamlit as st

markdown_text = "大学生志愿投入对生命意义感的影响调查，亲爱的同学：您好！非常感谢您能参与本次调查，这是一项关于志愿投入对生命意义感影响的调查，您的参与对于该调查非常重要，请注意：您的答案没有对错之分，请您根据自己的真实情况勾选对应选项，认真作答，不要漏题。本人郑重承诺，您的问卷仅作为研究参考数据，任何其他人员（老师、家长）都不会看到您的信息，请放心填写，感谢您的支持与配合！第一部分为基本情况，包含以下问题：1.你的性别：男、女；2.你的年级：大一、大二、大三、大四、研一、研二、研三及以上；3.你的专业：文科类、理科类、工科类、艺术体育类、经管类、其他；4.你的生源地：农村、城镇、城市；5.是否独生子女：是、否；6.你的政治面貌：中共党员（含预备党员）、共青团员、群众、其他；7.是否有过志愿服务经历：有、无；8.在过去一年中参与志愿服务的平均频率是：每月少于1次、每月1-2次、每周1次、每周多次；9.参加志愿服务的主要途径：学校/学院/班级统一组织、公益社团/志愿队招募、线上公益平台自主报名（如志愿汇、蚂蚁森林公益等）、亲友/老师推荐、其他（请注明）；10.参与志愿服务的主要形式是：纯线下（如实地帮扶、现场服务）、纯线上（如线上辅导、数据整理、虚拟宣传）、线上线下结合（如前期线上培训+后期线下服务）；11.参与志愿服务的原因：仅为获取学校要求的志愿学分/综测加分、主要为了学分，同时也想尝试志愿服务、主要为兴趣/提升自我/帮助他人/结交朋友等，学分只是附加收获、完全与学分无关，纯粹自愿参与；12.如果志愿服务不与学分挂钩，你是否还会参与：肯定不会、可能不会、可能会、肯定会；13.参加志愿服务主要是为了，请选择3-6项并排序：学习理解（学到知识、技能或社会实践经验等）、职业发展、价值表达、自我提升、自我保护（减轻负面感受或解决个人问题）、社会交往；接下来是志愿同侪影响相关量表，第一部分从从不、很少、有时、经常、总是维度评价：志愿服务团队其他成员分享的经验，会让我调整自己的服务方式；与志愿服务同伴的互动交流，改变了我的志愿服务观点、态度或行为；志愿服务团队成员发布的信息（如活动心得、服务技巧），会改善我在志愿服务时的态度或行为；在选择参与哪个志愿服务活动时，我会参考其他志愿者的评价；我会向志愿同伴收集活动相关信息，以便更好地完成服务任务；当我遇到服务难题时，我会主动询问其他志愿者是如何处理的；我会翻看志愿服务团队群聊或社交平台消息来了解活动情况；第二部分从非常不赞同、比较不赞同、一般、比较赞同、非常赞同维度评价：与志愿服务团队其他成员的观点保持一致，能够使我在团队中受到欢迎；与志愿服务团队其他成员的行为保持一致，会使我获得大家的认可；按照志愿服务团队的行为准则参与志愿活动能够符合大家的要求；与他人保持言行一致，对维系我和志愿服务团队成员间的关系非常重要；在志愿服务中，我会选择那些被大多数同伴认可的做法；我担心如果不遵守志愿服务团队的惯例，会被其他志愿者疏远；当我的服务方式与团队其他成员相似时，我会有一种归属感；第三部分从不符合、不太符合、一般、比较符合、非常符合维度评价：当志愿服务团队成员表达愉悦情绪时，我也会感到高兴；当志愿服务团队成员表达激动情绪时，我也会兴奋不已；当志愿服务团队成员表现出热情高涨时，我也会被带动起来；看到其他志愿者在服务中收获感动，我也会产生同样的温暖感受；当志愿服务团队的同伴对活动充满期待时，我也会对后续服务更加期待；当志愿服务团队成员表达愤怒情绪时，我也会心情不佳；当志愿服务同伴因服务受挫而表现出沮丧时，我的心情也会变差；第四部分从不符合、不太符合、一般、比较符合、非常符合维度评价：当我在志愿服务中遇到困惑时，志愿团队的同伴会为我提供帮助；当我的志愿服务建议被团队同伴采纳时，我会感受到被尊重；志愿服务团队的同伴认可我在活动中的付出和贡献；志愿团队的同伴会肯定我在服务中做得好的地方；参加志愿团队的集体活动，让我感到温暖和被接纳；与志愿服务团队的同伴在一起，能够缓解生活中的孤独感；通过参与志愿服务，我认识了更多志同道合的朋友；之后是志愿投入量表，从完全不符合、比较不符合、一般、比较符合、完全符合维度评价：在志愿服务中，我会运用自身所学的知识来完成服务任务；为了完成志愿服务，我会主动学习相关技能；志愿服务过程中，我会主动思考如何更好地完成任务；即使在空闲时间，我也会不自觉地思考与志愿服务相关的事情；我会根据服务任务的要求，调整和运用自己已有的经验；我会在服务过程中不断总结反思，以提升自己的服务表现；即使遇到没接触过的服务任务，我也能快速学习并上手；参与志愿服务时，我感到自己充满活力且干劲十足；参与志愿服务时，我感到自己精力充沛；参与志愿服务时，我会保持积极、热情的状态；我能持续做志愿服务很长时间，中间不需要休息；做志愿工作时，我沉浸其中，不会被旁的事干扰；即使志愿服务任务繁重，我也不会轻易感到疲惫；即使在服务中遇到困难，我也能坚持不退缩；我把志愿服务当作自己分内的事；我会对自己负责的服务任务尽心尽力，力求做好；即使没有人要求，我也会主动承担志愿服务中的任务；我愿意为志愿服务付出额外的时间和精力；看到服务对象需要帮助，我会主动上前提供支持；参与志愿服务时，我会对服务结果负责；作为一名志愿者，我感到自豪并愿意为之付出；在志愿服务中，我会真心关心服务对象的感受和需求；看到服务对象遇到困难，我会感同身受并想帮助他们；与服务对象交流时，我会用心倾听他们的想法；我会设身处地为服务对象着想；与服务对象互动时，我能感受到彼此之间的情感联结；在志愿服务中，我会主动关心同伴的状态和感受；参与志愿服务让我和团队同伴之间建立了深厚的情谊；再之后是自我概念清晰度量表，从非常不同意、比较不同意、不确定、比较同意、非常同意维度评价：我对自己的看法常常会相互矛盾；有时候我觉得我所表现出来的并不是真正的我；我很少感觉到自己人格的不同方面会互相冲突；我对自己不同角色的期待是一致的；我的价值观和行为方式之间很少有冲突；即使在不同情境下，我表现出的自我也是协调的；我对自己的看法可能今天一种，明天又是另外一种；我对自己的看法经常改变；在不同的情境下，我仍然知道自己是谁；即使经历了一些事情，我对自己的核心认识依然不变；当我回想过去的自己时，我不确定自己过去到底是一个什么样的人；如果有人要我描述我的个性，我可能每天的说法都不一样；一般来说，我对于自己是个什么样的人有很清楚的认识；即使我想跟别人说我是个什么样的人，我觉得自己也很难说清楚；有时候我觉得我对别人的了解多于对自己的了解；我能够清楚地描述自己的性格特点；我对自己想要什么样的生活有清晰的认知；我了解自己的优点和缺点分别是什么；我会花很多时间疑惑自己到底是个什么样的人；我对自己的看法是确定的，不会轻易怀疑；做决定对我来说通常很难，因为我不太清楚自己究竟想要什么；我相信自己对自己的判断是准确的；当别人对我的看法不同时，我仍然相信自己的判断；我对自己的认识有充分的信心；最后是生命意义感量表，从完全不符合、比较不符合、不确定、比较符合、完全符合维度评价：我追求生命里的一个或多个宏大的目标；我高度坚持生活中的某些核心目标；我的日常活动和远大的人生目标相吻合；我有一系列能够给予我人生方向感的核心目标；我的人生中有一些值得努力追求的目标；我的人生中有一些对我而言至关重要的目标；我生命中发生的大多数事情很合理；总体上来说，我能够理解身边的世界；我能够很容易地理解我的人生；我能够理解我的人生是为了什么；我能够理解生活中所发生的事情；从整体上审视我的人生，事情变得清晰明了；我的存在是很重要的；我的人生充满价值；每天我都体会到人生是值得的；我的存在并没有什么特别之处；我当下是否存在这件事依然意义重大；就算考虑到宇宙的浩瀚无垠，我仍可以说我的生命是有意义的。"

def _llm_convert(markdown_text: str) -> list[dict]:
    """
    ┌──────────────────────────────────────────────────────────────────────────┐
    │  REAL LLM INTEGRATION POINT                                              │
    │  Uncomment and configure when you have an API key.                       │
    │                                                                          │
    │  The prompt instructs the model to output ONLY a JSON array matching     │
    │  our schema.  No preamble, no markdown fences.                           │
    └──────────────────────────────────────────────────────────────────────────┘
    """
    # ── Option A: OpenAI ─────────────────────────────────────────────────────
    # from openai import OpenAI
    # client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     response_format={"type": "json_object"},
    #     messages=[
    #         {"role": "system", "content": _build_conversion_system_prompt()},
    #         {"role": "user",   "content": markdown_text[:12000]},
    #     ],
    # )
    # raw_json = response.choices[0].message.content
    # return json.loads(raw_json).get("questions", [])

    # ── Option B: Anthropic Claude ───────────────────────────────────────────
    # import anthropic
    # client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    # msg = client.messages.create(
    #     model="claude-opus-4-5",
    #     max_tokens=4096,
    #     system=_build_conversion_system_prompt(),
    #     messages=[{"role": "user", "content": markdown_text[:12000]}],
    # )
    # raw_json = msg.content[0].text
    # # Strip accidental markdown fences the model might add
    # raw_json = re.sub(r'^```json\s*|\s*```$', '', raw_json.strip())
    # return json.loads(raw_json).get("questions", [])

    # ── Option C: My GLM ───────────────────────────────────────────
    import requests
    API_KEY = st.secrets["ZHIPU_API_KEY"]
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "GLM-4.6V-Flash",
        "messages": [
            {"role": "system", "content": _build_conversion_system_prompt()},
            {"role": "user",   "content": markdown_text},
        ],
        "stream": False,
        "thinking": {
            "type": "disabled"
        }
    }
    response = requests.post(url, headers=headers, json=data, timeout=120)
    print(response)
    result = response.json()
    raw_json = result['choices'][0]['message']['content']

    text = raw_json.strip()
    # 去开头的 ```json 或 ```
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    # 去结尾的 ```
    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text.strip()).get("questions", [])


def _build_conversion_system_prompt() -> str:
    """
    System prompt used when calling a real LLM for Markdown → JSON conversion.
    Kept separate so it can be tuned without touching pipeline logic.
    """
    return """
You are a survey-parsing assistant.
INPUT:  Markdown text scraped from a survey web page.
OUTPUT: A single JSON object with one key "questions", containing an array.

Each element in the array MUST follow this exact schema:
{
  "question_id"   : "Q1",            // sequential, e.g. Q1 Q2 Q3 …
  "question_text" : "<full text>",
  "question_type" : "<type>",        // MUST be one of the six values below
  "options"       : ["<opt1>", …],   // empty array [] for open/fill/rating
  "is_required"   : true | false     // true if the survey marks it required
}

Allowed question_type values (use exactly these strings):
  single_choice   – radio buttons, one answer allowed
  multiple_choice – checkboxes, multiple answers allowed
  matrix          – grid/table of sub-questions sharing the same scale
  fill_in_blank   – short free-text or number entry
  rating          – numeric scale (NPS, stars, Likert with no explicit options)
  open_text       – long free-text / essay box

Rules:
- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.
- If a question's type is ambiguous, choose the closest match.
- Ignore navigation text, progress bars, page titles, and form submit buttons.
- Preserve the original question wording exactly.
""".strip()

print(_llm_convert(markdown_text))

# import requests
# import streamlit as st
# API_KEY = st.secrets["ZHIPU_API_KEY"] #"e3906d9880e3416bbb90e2810c25c374.t3FEUp13B3FuGqSi"
#
# url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
# headers = {
#     "Authorization": f"Bearer {API_KEY}",
#     "Content-Type": "application/json"
# }
#
# data = {
#     "model": "GLM-4.6V-Flash",
#     "messages": [
#         {"role": "user", "content": "你好"}
#     ],
#     "stream": False,
#     "thinking": {
#         "type": "disabled"
#     }
#
# }
#
# response = requests.post(url, headers=headers, json=data, timeout=30)
# result = response.json()
#
# print(result['choices'][0]['message']['content'])
