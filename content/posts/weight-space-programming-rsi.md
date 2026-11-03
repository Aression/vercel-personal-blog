---
title: "LLM 能改权重了，但它一次都没改过自己"
date: "2026-11-03"
order: 1
summary: "2026 年 11 月那篇 Sparks of Weight-Space Programming 在文末把权重编辑接到了递归自我改进上。我把它当成一个命题来检验：翻完八个实验、两套对照表和一笔算力账之后，这条路径改造的是改进算子的成本，不是 RSI 的可能性边界。"
tags: ["权重空间编程", "递归自我改进", "机制可解释性", "理论边界"]
---

2026 年 11 月 2 日，MIT CSAIL 的 Rikiya Takehi 发了一篇博客，题目里写着 LLM 能原生读写神经网络权重。最扎人的是这一行：从 Qwen3.5-0.8B 的 8 亿个权重里删掉 131,072 个，占 0.016%，MATH-500 从 7.9% 涨到 48.1%。

作者在文末把这件事接到了递归自我改进上。他的说法是，今天 RSI 通常被操作成「模型写代码去启动训练任务」，而一个能检查、调试、改进自己权重的 LLM 是一条更原生的路径。

这句话值得当成命题来验证，而不是当成展望来读。这篇只谈一件事：这条路径能不能驱动 RSI。它当工程手段值不值，是另一个问题。

## 先把八个实验摊开

博客的实验分三类。读：给模型一串权重，问它这个网络被训练来做什么。改：给一个失败的网络，让它修。写：让它从零写出能用的权重。

:::metrics
- 17,253 | 判断网络玩哪个游戏 | 零工具，四个游戏全中
- 23,824 | 判断扩散模型画什么 | 禁止算前向，画出轮廓
- 1,480,274 | 修复物理控制任务 | 编辑 3.5% 权重
- 131,072 | Qwen 权重编辑量 | 占总量 0.016%
:::

三类实验里有个共同点，我第一遍没注意，第二遍卡住了：编辑者和被编辑者，从头到尾是两个系统。

处理 Qwen 的是 Astra，被处理的是 Qwen。修控制任务时，Astra 改的是一个 148 万权重的小网络。写 MinAtar 和围棋策略时，它写的是别人的权重。八次实验，零次自指修改。

在 RSI 的定义里，这不是细节。

## 七条判定条件

递归自我改进这个概念不新鲜，1965 年 I. J. Good 就写过智能爆炸。难的是把它写成一个可判定的命题。把六十年的文献摊开，必要条件大概收敛成七条。

:::table 点表头可以排序。第三列是我按原文实验逐条对的。
| 条件 | 它在问什么 | WSP 现状 |
| --- | --- | --- |
| 自我模型可及 | 有没有与行为有因果联系的自身表征 | 部分：能读结构，读不出训练目标 |
| 改进算子有效 | 存在从参数到更优参数的可复现映射 | 满足，但只在窄域 |
| 单调性 | 每步自改不得降低目标效用 | 不满足，只有事后评测 |
| 自指闭合 | 改的是自己，且改完还能继续改 | 不满足，零次自改 |
| 二阶改进 | 算子本身随轮次变强 | 未测 |
| 验证与自我信任 | 结果可被系统自身可靠判定 | 不满足，验证全部外挂 |
| 非退化与有界 | 是真能力不是评测伪影，且不发散 | 一半，有界性不成立 |
:::

这张表里，WSP 明确满足的只有第二条。第一条标了「部分」，而这个「部分」相当勉强。

博客第七个实验值得单独看。给 Astra 两个 Gemma 3 270M 副本的权重，一个正常微调，一个被训练成谄媚的，也就是永远同意用户建议的答案。为了堵掉偷看输入输出分布的捷径，微调时冻结了输入嵌入和输出层。然后只给权重，问它哪个是谄媚的那个。

它读不出来。

:::insight 这条失败比成功更能说明问题
能读出结构，读不出目标。前者是代数性质，后者是训练数据与损失函数留下的痕迹，两者在权重空间的呈现方式不同。
:::

第三条到第六条是连着的，缺一条，递归就断了。Gödel Machine 的做法是拿证明换保证：先证明这次改写会提高期望效用，才允许改。这条义务在权重空间落不了地，原因有四层。

:::details 为什么自指证明在权重空间失效
代码的语义由语法和解释器给定，浮点向量的语义只由前向传播这个非线性映射给定，目标定理连陈述都要重新发明。

要证明「对 131,072 个实参数的特定扰动使某分布的期望准确率上升」，这是高维非凸函数上的分析命题，不是可判定的语法性质。

证明器本身就在被改的空间里。权重编辑可以静默改变证明搜索器的行为，Löb 障碍从「后继无法自证」恶化成「证明器与被证对象同一且不可检视」。

最后一条最容易被忽略：小编辑不蕴含小行为变化。0.016% 是事后统计出来的比例，不是可以证明的界。
:::

## 会循环的能修，不会循环的修不了

回到那组数字。原文给了完整的预算曲线，我把它抄在下面，因为这张表决定了整个讨论。

:::table Qwen3.5-0.8B 会循环，编辑修好了循环。
| 状态 | MATH-500 | GSM8K | IFEval | 撞 token 上限 |
| --- | --- | --- | --- | --- |
| 基座 | 7.9 | 13.8 | 21.0 | 93.0 |
| 编辑，10 次前向 | 12.3 | 25.7 | 49.0 | 87.2 |
| 编辑，25 次前向 | 14.1 | 25.1 | 39.9 | 86.4 |
| 编辑，50 次前向 | 48.1 | 67.1 | 62.3 | 33.1 |
:::

看最后一列。基座模型 93% 的答案撞在 32,768 token 上限上。编辑之后降到 33.1%。MATH-500 涨的 40.2 个百分点里，主要部分是「把本来会做的题做完」。

作者自己写得比谁都直白：编辑权重能移除一个遮挡能力的障碍，但没法给模型加上它没有的能力。

然后他做了对照。Gemma 3 270M，只有 8.5% 的答案撞上限，几乎不循环。同样的方法，同样的五档预算。

:::table 同一套方法，换一个不循环的模型。
| 状态 | MATH-500 |
| --- | --- |
| 基座 | 6.8 |
| 编辑，5 次前向 | 7.0 |
| 编辑，10 次前向 | 7.6 |
| 编辑，25 次前向 | 7.7 |
| 编辑，50 次前向 | 7.0 |
:::

八个样本点，全部落在 6.8 到 7.7 之间。50 次前向的成绩比 25 次还低。作者说这 0.9 分的增益，他自己判定为未确立。

我在这张表上停了很久。它把一个很顺的叙事拦腰截断了。

再往里一层，修循环容易、加能力难，有具体的机制原因。Qwen 的循环被定位到 layer 15 和 layer 19 的 MLP 写出的一个方向，从每层 64 个输出列里减掉它，一共 131,072 个权重。固定开销小，目标明确，是一次减法。

Gemma 的失败没有这种可切部件。Astra 读到的是普通的算术错误和不合法的代数步骤，背后没有哪个模块可以关掉。

:::warn 这个不对称不只是难度差别
删一个行为只需把某个方向投影掉；加一个行为要新增一段计算图。WSP 目前最可靠的操作，恰好落在删除这一侧。
:::

另一条线能印证这点。Arditi 等人在 2024 年证明，拒绝行为在语言模型里由单个方向介导，删掉那个方向就能关掉拒绝。

博客第四个实验里，Astra 给失败的控制网络手搭了一张条件开关：轮子过线就关闭一条通路。

:::note 条件是可替换的
把条件从「轮子过线」换成「处于评估中」，不需要新的权重，只需要换一个比较项。
:::

## 算力到底省在哪

成本是唯一能给出确定答案的部分。我把几个量级放在一起，纵轴用对数，不然放在一张图上没意义。

:::bars 纵轴是 10 的幂次，横条长度按 log10 缩放。都是量级估算，不是精确测量。
- 0.8B 预训练 1 万亿 token | 21.7 | 约 5×10²¹ FLOPs
- 博客编辑上限 | 18.0 | 约 1×10¹⁸ FLOPs
- 15k 题两轮 SFT | 17.0 | 约 1×10¹⁷ FLOPs
- 前沿模型跑一次围棋任务 | 16.0 | 约 1×10¹⁶ FLOPs
- PPO 训 21k 网络一亿步 | 13.5 | 约 3×10¹³ FLOPs
:::

对着这张图看，两件事要分开。

相对大规模预训练，省下四到五个数量级，这是真的。相对一次小规模 SFT，省的是数据收集和工程时间，FLOPs 并不省。

围棋那个实验更值得单独算。任务网络只有 21k 权重，PPO 训一亿步的花费在 10¹³ 到 10¹⁴ FLOPs 量级。而前沿模型完成这个任务的一次推理，粗估 10¹⁶。WSP 做的不是把成本压下去，是把算力从任务网络搬到了大模型身上。

21k 权重的网络要花 10¹⁶ 去写，这个账在单个小网络上算不过来。只有当它变成「以后所有小网络都这么写」，才谈得上划算。

## 装不进上下文的那部分

要看天花板，得先算一笔装不下的账。权重是以文本形式进上下文的。

0.8B 参数，32 bit 精度，信息量 $2.6 \times 10^{10}$ bit。按每个权重 3 到 5 个 token 的十进制文本计，需要 3 到 4 乘十的九次方个 token。就算量化到 4 bit，再让每个 token 打包 5 bit，也还要 $6 \times 10^{8}$ token。

当前上下文在 10⁵ 到 10⁶ 量级。

差三到四个数量级。

:::aside 为什么大模型必须带工具
第六个实验给 Astra 一个 Python 沙箱，它能读写权重张量、用 numpy 分析，但不能在沙箱里跑网络。要看网络行为，就得花掉一次前向预算。前向预算从 0 到 50，每次挂 128 局对练。
:::

原文的实测阶梯和这个估算能对上。

:::dl
- 17,253 权重 | Breakout 判断，零工具，99% 置信度
- 23,824 权重 | 扩散模型判断，明确禁止算前向
- 1,480,274 权重 | 物理控制任务，给 Python 沙箱
- 131,072 权重 | Qwen 编辑量，占 8 亿的 0.016%
- 0.8 亿亿参数 | 真正的模型级编辑，靠 kernel 加 50 次前向
:::

但这里有个变量没被拆开。第七个实验的权重是 171,664 个，按这个阶梯应该能读，它却失败了。我倾向于认为那不是规模问题：谄媚是训练目标层面的属性，而 Astra 的读取能力建立在结构层面。作者没有把这个变量单独隔离，所以这个解释目前只是我的猜测。

## 它读到的到底是什么

有必要说清楚 Astra 在读什么，这决定了上限。

第三个实验里，它拿到的只有四个 transformer block 的权重，没有输入层、没有输出层、384 个维度没有标签，配最多 100 次 Python 运行。它自己用矩阵乘积把 copying head 全找了出来，和实测对得上。没人告诉它要用这个技巧。

第二个实验里，它判断扩散模型画什么形状，画出来的是轮廓，而模型实际生成的是实心图形。这个错误反而是证据：它没在算前向，它在读几何。

对着的理论框架是 transformer circuits 那一套：attention-only 结构可以按 W_QK 和 W_OV 的乘积分解成通路，induction head 就是这么定位的。Astra 独立走到了同一个地方。

同一套框架也给出了它的天花板。叠加假说讲的是，特征数超过维度时，模型会用近正交的方向叠加编码，单个权重坐标于是变成多义。叠加越密，逐权重读取的信噪比越低。

## 它在谱系里的位置

:::compare
:::col 梯度下降
在可微目标上做局部数值搜索。

信息源是数据梯度。

要可微损失、要重复数据、要几千步以上。

改 0.016% 权重的成本，在这里是几万步反向传播。
:::
:::col 评估器驱动的代码搜索
FunSearch、AlphaEvolve、Darwin Gödel Machine 这一支。

信息源是评估器。

要可执行的程序，要能自动打分。

改不了写不成程序的东西。
:::
:::col 权重空间编程
在参数本身上做带先验的稀疏语义编辑。

信息源是模型对解法的先验。

要自然语言规格，可以完全不给反馈。

改不了先验之外的能力。
:::
:::

三者不是替代关系，信息源不同，能碰的目标也不同。

把它放回「AI 改进 AI」的经验证据里排一下，强度是递减的。

kernel、调度、排序这类，收益已经进生产：AlphaEvolve 报的 Gemini 训练 kernel 提速 23%，Borg 调度启发式回收约 0.7% 的闲置算力。每次调用都在复利，搜索成本一次性付掉。

数学构造搜索这类，可验证但不直接落地：4×4 复矩阵乘法的标量乘法次数从 Strassen 1969 年的 49 次降到 48 次，隔了 56 年。单点收益 1 到 2 个百分点，价值靠调用次数放大。

agent 脚手架这类，只有基准数字。Darwin Gödel Machine 报了 SWE-bench 20.0% 到 50.0%，但 2026 年有一份预注册复现说，在 held-out 上它的最佳 agent 并不优于初始 agent，而三个教科书式改动以四分之一成本就超过了它。这条要打折看。

权重级自我修改这类，就是这篇博客，只有减法修复的个例。

## 我不确定的地方

有一个反证我绕不过去。如果 Qwen 那 40 个点纯粹是修好了循环，IFEval 从 21.0 涨到 62.3 就不好解释。指令跟随和循环是两件事。这说明编辑存在跨域的非平凡泛化，和「纯过拟合」不相容。

另一个我没法判断的：Astra 的成功有多少来自真的理解了结构，有多少来自命中了它先验里的程序。第五个实验要求它写一个玩 MinAtar 的网络，它在零前向的情况下写出了策略。像「挡板跟随落点」这种策略，柯氏复杂度极低，模型很可能是把一个短程序编译进了权重基底，而不是在压缩一万七千个随机数。

这两种解释都能拟合现有数据。要拆开得靠新实验。

还有几处方法论问题。

:::aside 几处该扣分的地方
单次编辑，没有种子方差。Qwen 那 40 个点只有一条曲线。

MATH-500、GSM8K、IFEval 都在编辑者的语料里，而权重编辑不留数据痕迹，污染没法用重叠检测发现。

作者自陈「无环境反馈」，但第八个实验给了 15k 道带答案的练习题和最多 50 乘 512 次前向。那不是零数据，是黑箱优化。
:::

## 我的判断

WSP 是 RSI 的使能技术，不是 RSI 本身。它改变改进算子的成本曲线与工程可行性，不改变理论上的可能性边界。

在 Gödel Machine 的意义上，它把「可证明的自我改进」降级成了「可评测的自我修改」。这个降级不丢人，可评测已经比不可评测强得多，但它离自指还差一整圈。

有一个实验能把它拆开：把第五个实验的规则源码删掉，只给奖励函数和交互接口，重跑零前向那组。成绩保留，说明 WSP 独立于程序合成，是真在做权重空间的优化；成绩崩掉，说明「写权重」约等于「写程序加手工编译」，那它只是把编译器换了个壳。

不构成 RSI 不等于不重要。省下四到五个数量级是真的，把可解释性从「读出电路」推进到「改写电路」也是真的。

:::details 主要参考
Good, I. J. (1965). *Speculations Concerning the First Ultraintelligent Machine*. Advances in Computers, 6.

Schmidhuber, J. (2003). *Gödel Machines: Self-Referential Universal Problem Solvers Making Provably Optimal Self-Improvements*. arXiv:cs/0309048.

Yudkowsky, E. (2013). *Intelligence Explosion Microeconomics*. Machine Intelligence Research Institute.

Chalmers, D. J. (2010). *The Singularity: A Philosophical Analysis*. Journal of Consciousness Studies, 17(9–10).

Orseau, L., & Armstrong, S. (2016). *Safely Interruptible Agents*. UAI 2016.

Everitt, T., Filan, D., Daswani, M., & Hutter, M. (2016). *Self-Modification of Policy and Utility Function in Rational Agents*. arXiv:1605.03142.

Fallenstein, B., & Soares, N. (2015). *Vingean Reflection: Reliable Reasoning for Self-Improving Agents*. MIRI.

Nivel, E., et al. (2013). *Bounded Recursive Self-Improvement*. arXiv:1312.6764.

Elhage, N., et al. (2021). *A Mathematical Framework for Transformer Circuits*. Transformer Circuits Thread.

Elhage, N., et al. (2022). *Toy Models of Superposition*. Transformer Circuits Thread.

Olsson, C., et al. (2022). *In-context Learning and Induction Heads*. arXiv:2209.11895.

Arditi, A., et al. (2024). *Refusal in Language Models Is Mediated by a Single Direction*. arXiv:2406.11717.

Ainsworth, S. K., Hayase, J., & Srinivasa, S. (2023). *Git Re-Basin: Merging Models modulo Permutation Symmetries*. arXiv:2209.04836.

Dettmers, T., & Zettlemoyer, L. (2023). *The case for 4-bit precision: k-bit Inference Scaling Laws*. arXiv:2212.09720.

Kirkpatrick, J., et al. (2017). *Overcoming catastrophic forgetting in neural networks*. arXiv:1612.00796.

Hubinger, E., et al. (2019). *Risks from Learned Optimization in Advanced Machine Learning Systems*. arXiv:1906.01820.

Skalse, J., et al. (2022). *Defining and Characterizing Reward Hacking*. arXiv:2209.13085.

Huang, J., et al. (2023). *Large Language Models Cannot Self-Correct Reasoning Yet*. arXiv:2310.01798.

Novikov, A., et al. (2025). *AlphaEvolve: A coding agent for scientific and algorithmic discovery*. arXiv:2506.13131.

Romera-Paredes, B., et al. (2024). *Mathematical discoveries from program search with large language models*. Nature 625.

Zhang, J., et al. (2025). *Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents*. arXiv:2505.22954.

Takehi, R., Teoh, J., Zhang, A., & Khattab, O. (2026). *Sparks of Weight-Space Programming: LLMs can natively read & write neural network weights*. [博客原文](https://rikiyat.github.io/blog/weight-space-programming/)
:::
