

==============================================================================
FILE: [01]_Integrated_Sensing_and_Communication_for_Low-Altit_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> 1 Integrated Sensing and Communication for Low-Altitude Security Ruixing Ren İD ,Graduate Student Member, IEEE, Abstract—The dense concentration of low-altitude, slow-speed, and small-size targets in the complex low-altitude environment poses significant security challenges, including failures in contin- uous wide-area sensing and ambiguous target intent, which exist- ing regulatory frameworks struggle to address. Integrated sensing and communication (ISAC), a hallmark of next-generation mobile communication, offers a transformative approach to low-altitude security governance. By leveraging existing cellular infrastructure and spectrum resources, ISAC enables the construction o

[ABSTRACT]
The dense concentration of low-altitude, slow-speed, and small-size targets in the complex low-altitude environment poses significant security challenges, including failures in contin- uous wide-area sensing and ambiguous target intent, which exist- ing regulatory frameworks struggle to address. Integrated sensing and communication (ISAC), a hallmark of next-generation mobile communication, offers a transformative approach to low-altitude security governance. By leveraging existing cellular infrastructure and spectrum resources, ISAC enables the construction of a seamless wide-area sensing network, supports intelligent feature extraction and intent inference, facilitates real-time collaborative decision-making, and establishes a dynamic trust authentication framework. This article systematically reviews the technical system, analyzes the security challenges, forecasts the enabling value of ISAC, and discusses the resulting open problems and challenges, thereby laying a foundation for future research and industrial implementation.

[HEADINGS]
I. INTRODUCTION
II. SECURITYANALYSIS OFLOW-ALTITUDESCENARIOS
  A. Physical and Motion Characteristics of Low-Altitude Tar-
  B. Key Security Challenges
III. ISAC-ENABLEDLAS
  A. Wide-Area Continuous Seamless Sensing Network
  B. Intelligent Feature Extraction and Intention Understanding
  C. Real-Time Collaborative Situation Sharing and Decision
  D. ISAC-Based Dynamic Trusted Authentication System
IV. OPENPROBLEMS ANDCHALLENGES
  A. Sensing Performance Bottlenecks in Complex Environments
  B. Insufficient Generalization of Intelligent Cognition and
  C. Real-Time Guarantee for Low-Latency Collaborative
  D. Robustness Challenges of Security Authentication in Ad-
V. CONCLUSION

[CONTRIBUTION]
(none found)

[CONCLUSION]
This article focused on the deep integration of LAS and ISAC technology, conducting a systematic analysis around challenges, empowerment and prospects. First, it clarified the uniqueness of the LAE, which gives rise to four core secu- rity bottlenecks. Second, it elaborated on the empowerment pathways of ISAC technology. Finally, it identified the key challenges in the current implementation of the technology. As the first overview of ISAC technology in the field of LAE, this article only presented a partial research landscape. However, it is hoped that the relevant discussions can stimulate academic interest and in-depth exploration in the future evolution of LAS. REFERENCES [1] J. Zhao, R. Ren, D. Zou, Q. Zhang, and W. Xu, “IoV-oriented integrated sensing, computation, and communication: System design and resource allocation,”IEEE Transactions on Vehicular Technology, vol. 73, pp. 16283–16294, Nov. 2024. [2] Y . Wang and et al., “Toward realization of low-altitude economy net- works: Core architecture, integrated technologies, and future directions,” IEEE Transactions on Cognitive Communications and Networking, vol. 11, pp. 2788–2820, Oct. 2025. [3] Y . Huang and et al., “An adaptive MDS-coded OFDM waveform for low-altitude ISAC: Design and optimization,”IEEE Journal on Selected Areas in Communications, pp. 1–1, 2025. <<<PAGE 7>>> 7 [4] J. Tang, Y . Yu, C. Pan, H. Ren, D. Wang, J. Wang, and X. You, “Co- operative ISAC-empowered low-altitude economy,”IEEE Transactions on Wireless Communications, vol. 24, pp. 3837–3853, May 2025. [5] Y . Jiang, X. Li, G. Zhu, and et al., “Integrated sensing and communi- cation for low altitude economy: Opportunities and challenges,”IEEE Communications Magazine, vol. 63, pp. 72–78, Dec. 2025. [6] R. Ren, J. Zhao, and Q. Zhang, “UA V-assisted collaborative sensing task offloading and resource allocation in IoV,”IEEE Transactions on Vehicular Technology, pp. 1–10, 2025. [7] C. Liu and et al., “UA V aided integrated sensing, communication and computing: Optimization via federated learning,”IEEE Transactions on Vehicular Technology, pp. 1–13, 2025. [8] Z. Ma, Y . Liang, Q. Zhu, J. Zheng, Z. Lian, L. Zeng, C. Fu, Y . Peng, and B. Ai


==============================================================================
FILE: [02]_ISAC-Enabled_Multi-UAV_Collaborative_Target_Sensin_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> ISAC-Enabled Multi-UA V Collaborative Target Sensing for Low-Altitude Economy Rui Wang1, Kaitao Meng 2, Deshi Li 1, and Liang Xu 1 1Electronic Information School, Wuhan University, Wuhan, China. 2Department of Electrical and Electronic Engineering, The University of Manchester, Manchester, UK. Emails: 1{ruiwang, dsli, lgxu}@whu.edu.cn, 2kaitao.meng@manchester.ac.uk Abstract—Integrated sensing and communication (ISAC) has attracted growing research interests to facilitate the large-scale development of the low-altitude economy (LAE). However, the high dynamics of low-altitude targets may overwhelm fixed ISAC systems, particularly at the edge of their coverage or in blind zones. D

[ABSTRACT]
Integrated sensing and communication (ISAC) has attracted growing research interests to facilitate the large-scale development of the low-altitude economy (LAE). However, the high dynamics of low-altitude targets may overwhelm fixed ISAC systems, particularly at the edge of their coverage or in blind zones. Driven by high flexibility, unmanned aerial vehicle (UA V)-assisted ISAC can provide more freedom of design to enhance communication and sensing abilities. In this paper, we propose an ISAC-enabled multi-UA V dynamic collaborative target sensing scheme, where UA Vs can dynamically adjust their flight and resource allocation for cooperative sensing of mobile target through communicating with the terrestrial cellular network with ISAC signals. To achieve the precise sensing of the dynamic target, the posterior Cram ´er-Rao bound (PCRB) for the target state is derived. Subsequently, the PCRB minimization problem is formu- lated by jointly optimizing the UA V-BS association, UA Vs’ trajec- tories and bandwidth allocation, subject to the communication requirements for the UA Vs. However, the problem is challenging since it involves non-convex and implicit objective function with coupled optimization variables. For a fast implementation of sens- ing and tracking, we propose a low-complexity iterative algorithm that can efficiently obtain a sub-optimal solution to the problem. Specifically, the UA V-BS association is first determined by the communication-optimal solution. Then the UA Vs’ trajectories and bandwidth allocation are alternatively optimized based on the descent direction search algorithm. Finally, numerical results are provided to validate the superiority of our proposed designs as compared to various benchmarks.

[HEADINGS]
I. INTRODUCTION
II. SYSTEMMODEL ANDPROBLEMFORMULATION
  A. Communication Model
  B. Sensing Model
  C. Dynamic Target Sensing Mechanism
  D. Problem F ormulation
III. COMMUNICATION-CONSTRAINEDSENSINGERROR
  B. Proposed Algorithm for ISAC Solution
IV. SIMULATION ANDRESULTSANALYSIS
V. CONCLUSION

[CONTRIBUTION]
ution. First, a communication-optimal solution is obtained to check the feasibility and determine the UA V-BS association. Then, the alternating optimization (AO) framework is employed to optimize the UA V trajectory and bandwidth allocation based on the descent direction search algorithm. The main contributions are summarized as follows: •We propose an ISAC-enabled multi-UA V dynamic col- laborative target sensing scheme, where UA Vs can dy- namically adjust their flight and resource allocation for cooperative sensing of mobile target. •We develop a low-complexity iterative algorithm for joint optimization of the UA V-BS association, UA Vs’ trajecto- ries and bandwidth allocation to minimize the PCRB of the target state, while satisfying the transmission require- ment and reliable control of the UA Vs. •Simulation results show that the proposed scheme can effectively improve the sensing performance and reduce the estimated error in target location and velocity. II. SYSTEMMODEL ANDPROBLEMFORMULATION As shown in Fig. 1, consider an ISAC-enabled multi-UA V collaborative sensing scenario consisting ofMUA Vs,KBSs, and one target. The UA Vs transmit the obtained sensing data to BSs, while reusing the information signals for target sensing at the region of interest. The BSs not only receive the sensing data from UA Vs for further processing, but also manage the wireless resources and

[CONCLUSION]
In this paper, an ISAC-enabled multi-UA V dynamic col- laborative target sensing scheme was proposed to support the development of LAE. Specifically, multiple UA Vs can exploit ISAC signals to collaboratively conduct sensing of the mobile target while communicating with the terrestrial BSs. To achieve the precise sensing of the dynamic target, the PCRB for the target state was derived as the sensing error metric. Then, we formulated an optimization problem aiming at minimizing the PCRB by optimizing the UA V-BS association, UA Vs’ trajectories and bandwidth allocation. To tackle the formulated non-convex problem, we proposed a low-complexity iterative algorithm to solve it efficiently. First, a communication-optimal solution was obtained to check the feasibility and determine the UA V-BS association. Then, AO framework is employed to alternatively optimize the UA Vs’ trajectories and bandwidth allocation based on the descent direction search algorithm. The simulation results show the effectiveness and superiority of our proposed designs as compared to various benchmarks. In the future, we look forward to exploring the use of the ISAC multi-UA V collaborative network for multi-target tracking and integrating computing capabilities to provide more robust and intelligent services. REFERENCES [1] Y . Jiang, X. Li, G. Zhu, H. Li, J. Deng, K. Han, C. Shen, Q. Shi, and R. Zhang, “Integrated sensing and communication for low altitude economy: Opportunities and challenges,”IEEE Commun. Mag., pp. 1–7, Apr. 2025. [2] K. Meng, C. Masouros, K.-K. Wong, A. P. Petropulu, and L. Hanzo, “Integrated sensing and communication meets smart propagation engi- neering: Opportunities and challenges,”IEEE Netw., vol. 39, no. 2, pp. 278–285, Mar. 2025. [3] R. Wang, K. Meng, and D. Li, “Multi-UA V collaborative trajectory planning for seamless data collection and transmission,” in2025 IEEE Wireless Communications and Networking Conference (WCNC), Mar. 2025, pp. 1–7. [4] S. Al-Dharrab, “Detection performance of malicious UA V using massive iot networks,” in2023 IEEE 97th V ehicular Technology Conference (VTC2023-Spring), Jun. 2023, pp. 1–5. [5] F. Liu, Y . Cui, C. Masouros, J. Xu, T. X. Ha


==============================================================================
FILE: [03]_MIMO_OFDM-Enabled_ISAC_for_Low-Altitude_Non-Cooper_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 1 MIMO OFDM-Enabled ISAC for Low-Altitude Non-Cooperative UA V Surveillance: A Survey Shiyu Bai †,Member, IEEE,Sijia Li †,Graduate Student Member, IEEE,Cunyi Yin,Member, IEEE,Wenqiu Qu, Li-Ta Hsu,Senior Member, IEEE, Yuanwei Liu,Fellow, IEEE, Wen-Hua Chen,Fellow, IEEE Abstract—The widespread use of unmanned aerial vehicles (UA Vs) in low-altitude airspace has raised significant safety and security concerns, motivating the development of reliable non- cooperative UA V surveillance technologies. Integrated sensing and communication (ISAC), enabled by multiple-input multiple- output (MIMO) architectures and orthogonal freque

[ABSTRACT]
The widespread use of unmanned aerial vehicles (UA Vs) in low-altitude airspace has raised significant safety and security concerns, motivating the development of reliable non- cooperative UA V surveillance technologies. Integrated sensing and communication (ISAC), enabled by multiple-input multiple- output (MIMO) architectures and orthogonal frequency-division multiplexing (OFDM) waveforms, has emerged as a promising paradigm for leveraging cellular infrastructure to support large- scale sensing without additional hardware deployment. This paper presents the first comprehensive survey dedicated to MIMO OFDM-enabled ISAC for low-altitude non-cooperative UA V surveillance, where the targeted UA Vs do not intentionally assist the monitoring system through dedicated signaling or prior coordinate sharing. We first analyze the unique propagation characteristics of low-altitude UA V sensing, including severe clutter, rapid channel variations, and mixed near/far-field ef- fects, and discuss corresponding waveform design principles. We then systematically review existing MIMO OFDM-enabled UA V surveillance techniques along four key dimensions: ISAC system modeling and network optimization, UA V detection and tracking algorithms under single and networked base station (BS) archi- tectures, UA V identification techniques based on micro-Doppler and learning-based approaches, and experimental validations and practical field trials. Subsequently, we summarize open challenges such as sensing under severe clutter and multipath, data scarcity for identification, cooperative multi-BS fusion, and real-world deployment constraints. Finally, we outline promising future research directions toward 5G-Advanced (5G-A) and 6G-enabled low-altitude surveillance systems.

[HEADINGS]
I. INTRODUCTION
  A. Existing Surveys and Our Contributions
  B. Organization of this Article
II. FOUNDATIONS OFMIMO OFDM-ENABLEDISACFOR
  A. Received Signal Characteristics for UAV ISAC
  B. Signaling Design for MIMO OFDM ISAC
  C. ISAC in Mixed Near- and Far-Field Channel
III. MIMO OFDM-ENABLEDUAV SURVEILLANCE
  A. System Design and Optimization
  B. UAV Detection and Tracking
  C. UAV Identification
  D. Experimental Tests and Analysis
IV. OPENISSUES ANDFUTURERESEARCHDIRECTIONS
  A. Challenges
  B. Future Directions
V. CONCLUSION

[CONTRIBUTION]
non- cooperative UA V surveillance. Therefore, focusing on MIMO OFDM-enabled ISAC for low-altitude non-cooperative UA V surveillance, this work systematically reviews the state of the art in this field. Major abbreviations used in this article are summarized in Table I. A. Existing Surveys and Our Contributions Recently, several surveys have provided overviews of ISAC- based sensing technologies from different perspectives. 1) General ISAC Surveys:Aldirmaz-Colaket al.provided a comprehensive survey of ISAC for 6G networks from both sensing-centric and communication-centric perspectives [19]. Their study reviews key ISAC enablers such as waveform design, edge computing, and vehicular communications, and emphasizes security considerations as well as emerging di- rections including reconfigurable intelligent surface (RIS), non-orthogonal multiple access (NOMA), and UA Vs. It also highlights the rapidly growing role of artificial intelligence (AI) and machine learning (ML) in next-generation ISAC systems. However, this survey focuses on general ISAC ar- chitectures and does not analyze sensing techniques tailored for non-cooperative UA V surveillance. Similarly, Weiet al. provided a comprehensive overview of ISAC signal design, processing, and optimization [20]. However, UA V sensing and detection are only mentioned briefly as one of the potential future application scenarios, wit || , none has specifically addressed MIMO OFDM-enabled ISAC architectures for low- altitude non-cooperative UA V detection, tracking, and iden- tification. The comparison between existing surveys and this paper is provided in Table II. The overview of this paper is shown in Fig. 1. Therefore, the main contributions of this article are as follows: 1) To the best of our knowledge, this is the first survey that systematically reviews research on MIMO OFDM- enabled ISAC for low-altitude, non-cooperative UA V surveillance. 2) This paper analyzes the unique signal characteristics and propagation properties of low-altitude UA V sensing, and summarizes corresponding waveform design and receiver processing considerations for MIMO OFDM-based ISAC systems. 3) This paper presents a comprehensive and in-depth survey of MIMO OFDM-enabled UA V surveillance techniques, organized along four key dimensions: system design and optimization, detection and tracking, identification, and corresponding experimental tests and analyses. 4) This paper discusses the limitations and challenges of existing methods, and concludes by outlining promising directions for future research. B. Organization of this Article The rest of this article is structured as follows. Section II presents the foundations of MIMO OFDM-enabled ISAC for low-altitude UA V surveillance. In Sections III, MIMO OFDM-enabled UA V surveillanc

[CONCLUSION]
This paper has presented a comprehensive survey on MIMO OFDM-enabled ISAC for low-altitude non-cooperative UA V surveillance. We first examine the fundamental signal char- acteristics of low-altitude UA V sensing, including strong ground clutter, rapid channel variations, and mixed near-/far- field propagation, and review corresponding waveform design and modeling approaches. Building upon this foundation, we summarize existing UA V surveillance techniques from four perspectives, namely system design and optimization, detection and tracking, identification, and experimental vali- dation. Importantly, MIMO OFDM-enabled ISAC emerges as a practical core technology for low-altitude UA V surveillance, as OFDM waveforms enable delay-Doppler sensing within existing communication frameworks, MIMO provides high spatial resolution for target discrimination, and cellular infras- tructure reuse supports wide-area and persistent monitoring with low deployment cost. Despite substantial progress, sev- eral challenges remain, including robust sensing under dense clutter and multipath, scalable multi-BS cooperative fusion, and reliable identification under limited labelled data. Future research is expected to focus on multi-modal fusion, AI-driven sensing, and distributed ISAC architectures, toward practical and scalable low-altitude surveillance systems. ACKNOWLEDGMENTS This work was supported by the Hong Kong Polytechnic University Start-up Fund under the Strategic Hiring Scheme ti- tled “Suppressing Multipath-Induced False Alarms for Robust 5G mmWave UA V Detection via Geometric Channel Mod- eling” and the Research Centre for Low Altitude Economy (RCLAE), The Hong Kong Polytechnic University. REFERENCES [1] S. Wandelt, S. Wang, C. Zheng, and X. Sun, “AERIAL: A meta review and discussion of challenges toward unmanned aerial vehicle operations in logistics, mobility, and monitoring,”IEEE Transactions on Intelligent Transportation Systems, vol. 25, no. 7, pp. 6276–6289, 2023. [2] J. Rückin, F. Magistri, C. Stachniss, and M. Popovi ´c, “An informative path planning framework for active learning in UA V-based semantic mapping,”IEEE Transactions on Robotics, vol. 39, no. 6, pp. 42


==============================================================================
FILE: [04]_OFDM_Waveform_Optimization_for_Bistatic_Integrated_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> OFDM Waveform Optimization for Bistatic Integrated Sensing and Communications Ruolin Du ∗, Zhiqiang Wei ∗, Zai Y ang∗, Y a-Feng Liu†, Bingpeng Zhou ‡, and Derrick Wing Kwan Ng § ∗ School of Mathematics and Statistics, Xi’an Jiaotong University, Xi’an, China † School of Mathematical Sciences, Beijing University of Posts and Telecommunications, Beijing, China ‡ School of Electronics and Communication Engineering, Sun Y at-sen University, Shenzhen, China § School of Electrical Engineering and Telecommunications, University of New South Wales, Sydney, Australia Email: duruolin@stu.xjtu.edu.cn, {zhiqiang.wei, yangzai}@xjtu.edu.cn, yafengliu@bupt.edu.cn, zhoubp3@mail.sysu.edu.cn, w.k.

[ABSTRACT]
This paper investigates the design of orthogonal frequency-division multiplexing (OFDM) waveforms for bistatic integrated sensing and communication (ISAC) systems. In the considered framework, an ISAC transmitter jointly optimizes subcarrier assignment and power allocation for a single OFDM waveform that simultaneously supports communication and sens- ing functionalities. Meanwhile, an ISAC receiver decodes infor- mation on communication subcarriers and estimates per-path propagation delays via exploiting pilot symbols on sensing sub- carriers. We propose a joint path coefﬁcient and delay estimation (JPCDE) scheme, revealing that the achievable communication data rate (CDR) is determined by the number of communication subcarriers, whereas the delay sensing accuracy is governed by the index distribution of sensing subcarriers. Building on this insight, we formulate an OFDM waveform optimization problem to maximize the CDR subject to sensing-accuracy and power- budget constraints. To solve this problem, we employ a quadratic transform and Lagrangian dual decomposition, which iteratively updates the subcarrier assignment and power allocation variables in closed-form. Our results reveal that a subcarrier is allocated for sensing if and only if its Fisher information gain exceeds the corresponding communication rate loss, while the power allocation for communication subcarriers exhibits a bounded water-ﬁlling structure. Simulation results demonstrate that the proposed frameworks substantially outperform existing baselines in both delay estimation accuracy and CDR.

[HEADINGS]
I. I NTRODUCTION
II. B ISTATIC OFDM-B ASED ISAC S YSTEM MODEL
III. OFDM W AVEFORM OPTIMIZATION BASED ON JPCDE
  A. CRB Derivation
  B. Problem F ormulation
  C. Solution Approach
IV. S IMULATION RESULTS
V. C ONCLUSION

[CONTRIBUTION]
) can be decoupled into terms associated ex- clusively with sensing subcarriers and communication sub- carriers3. By applying Lagrangian dual decomposition, (11) can be decomposed as L(k) = L(k) c + L(k) r + λ(k)Preq − µ(k) maxp{Jreq,p}, where the communication-related (i.e., u(k) m = 0) Lagrangian contribution is given by L(k) c ≜ MX m=1 (1−u(k) m ) log2(1+ ||hm||2 2Pm σ2 )−λ(k) MX m=1 (1−u(k) m )Pm, (13) and the sensing-related (i.e., u(k) m = 1) Lagrangian contribution is given by L(k) r ≜ µ(k) MX m=1 u(k) m Pm(m − y(k))2 − λ(k) MX m=1 u(k) m Pm. (14) For subcarriers assigned for communication (i.e., u(k) m = 0), the objective function is given by (13). By exploiting the KKT optimality conditions [11], [20], the optimal power allocation on the m-th subcarrier used for communication is given by: P (k) m =  1 λ(k) ln 2 − σ2 ||hm||2 2 P0 0 , (15) where [x]b a = min{b, max{x,a }}. The power allocation solu- tion in (15) follows a bounded water-ﬁlling structure, where more power is allocated to subcarriers with higher channel conditions, i.e., those exhibiting higher channel gains ||hm||2 2. For subcarriers assigned for sensing (i.e., u(k) m = 1 ), the objective function is given by (14). The partial derivative of L(k) r with respect to (w.r.t.) Pm is given by ∂L(k) r ∂Pm =µ(k)(m −y(k))2 −λ(k). (16) The term (m−y(k))2 measures the squared distance in subcar- rier index space be || n be decomposed as L(k) = L(k) c + L(k) r + λ(k)Preq − µ(k) maxp{Jreq,p}, where the communication-related (i.e., u(k) m = 0) Lagrangian contribution is given by L(k) c ≜ MX m=1 (1−u(k) m ) log2(1+ ||hm||2 2Pm σ2 )−λ(k) MX m=1 (1−u(k) m )Pm, (13) and the sensing-related (i.e., u(k) m = 1) Lagrangian contribution is given by L(k) r ≜ µ(k) MX m=1 u(k) m Pm(m − y(k))2 − λ(k) MX m=1 u(k) m Pm. (14) For subcarriers assigned for communication (i.e., u(k) m = 0), the objective function is given by (13). By exploiting the KKT optimality conditions [11], [20], the optimal power allocation on the m-th subcarrier used for communication is given by: P (k) m =  1 λ(k) ln 2 − σ2 ||hm||2 2 P0 0 , (15) where [x]b a = min{b, max{x,a }}. The power allocation solu- tion in (15) follows a bounded water-ﬁlling structure, where more power is allocated to subcarriers with higher channel conditions, i.e., those exhibiting higher channel gains ||hm||2 2. For subcarriers assigned for sensing (i.e., u(k) m = 1 ), the objective function is given by (14). The partial derivative of L(k) r with respect to (w.r.t.) Pm is given by ∂L(k) r ∂Pm =µ(k)(m −y(k))2 −λ(k). (16) The term (m−y(k))2 measures the squared distance in subcar- rier index space between subcarrier m and the power-weighted spectral centroid y(k). Moreover, as L(k) r is linear w.r.t. Pm, a positive gradient in (16) implies that the optimal powe

[CONCLUSION]
(none found)


==============================================================================
FILE: [05]_Security_in_Low-Altitude_ISAC_with_Coupled_Communi_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> 1 Security in Low-Altitude ISAC with Coupled Communication and Sensing Information Leakage Meiding Liu,Graduate Student Member , IEEE, Yuyuan Fang,Member , IEEE, Zhengchun Zhou,Member , IEEE, Qiao Shi,Member , IEEE, and Pingzhi Fan,Life Fellow, IEEE Abstract—Secure information transmission in integrated sensing and communication (ISAC) systems deployed in low-altitude wireless networks (LA WN) is particularly challenging due to the open airspace and the broadcast nature of wireless signals reused for both communication and sensing, which give rise to more severe and complex security threats. This paper investigates the joint communication and sensing security of low-altitude ISA

[ABSTRACT]
Secure information transmission in integrated sensing and communication (ISAC) systems deployed in low-altitude wireless networks (LA WN) is particularly challenging due to the open airspace and the broadcast nature of wireless signals reused for both communication and sensing, which give rise to more severe and complex security threats. This paper investigates the joint communication and sensing security of low-altitude ISAC systems where a communication eavesdropper (CEve) cooperates with and assists a sensing eavesdropper (SEve), leading to coupled communication and sensing information leakage. We define a recoverable signal power ratio (RSR) that quantifies the degree of coupling between communication eavesdropping and sensing information leakage. Based on this coupling, we formulate a joint eavesdropping mutual information (MI) that facilitates unified analysis and optimization for the overall security. Subsequently, we design the transmit beamformer that maximizes the weighted sum of legitimate communication and sensing MI under the joint information-leakage constraint. Simulations show that the proposed scheme converges rapidly and effectively exploits the coupling between communication eavesdropping capability and sensing information leakage.

[HEADINGS]
I. INTRODUCTION
II. SYSTEMMODEL ANDPERFORMANCEMETRICS
  A. Legitimate Communication and Sensing
  B. Cooperative Communication and Sensing Eavesdropping
III. BEAMFORMINGDESIGN UNDERJOINT
  A. Problem F ormulation and Algorithm Design
  B. Convergence and Complexity Analysis
IV. NUMERICALRESULTS
V. CONCLUSION

[CONTRIBUTION]
(none found)

[CONCLUSION]
This paper investigated the joint communication and sensing security in low-altitude ISAC systems with cooperative CEve and SEve. To this end, we introduced the RSR to quantify the coupling between the communication eavesdropping recovery and the resulting sensing information leakage at the SEve. We also developed a joint eavesdropping MI metric to characterize this coupling and designed the transmit beamformer that maximizes the overall secure performance of legitimate communication and sensing while limiting joint information leakage. Finally, simulation results showed that the proposed scheme converges rapidly and that the RSR critically influences both sensing information leakage and overall security performance. REFERENCES [1] F. Liu, Y . Cui, C. Masouros, J. Xu, T. X. Han, Y . C. Eldar, and S. Buzzi, “Integrated sensing and communications: Toward dual-functional wireless networks for 6G and beyond,”IEEE J. Sel. Areas Commun., vol. 40, no. 6, pp. 1728–1767, Jun. 2022. [2] N. Su, F. Liu, and C. Masouros, “Secure radar-communication systems with malicious targets: Integrating radar, communications and jamming functionalities,”IEEE Trans. Wireless Commun., vol. 20, no. 1, pp. 83–95, Jan. 2021. [3] L. Cai et al., “Secure physical layer communications for low-altitude economy networking: A survey,”IEEE Commun. Surveys Tuts., vol. 28, pp. 2497–2530, 2026. [4] M. Liu et al., “Joint beamforming design for integrated sensing and communication systems with hybrid-colluding eavesdroppers,”IEEE Trans. Commun., vol. 73, no. 8, pp. 6484–6498, Aug. 2025. [5] M. Wu et al., “Secure split offloading and trajectory design for UA V-assisted multi-exit collaborative DNN inference,”IEEE Trans. Mobile Comput., early access, doi: 10.1109/TMC.2026.3708394. [6] M. Wu et al., “Security-aware designs of multi-UA V deployment, task offloading and service placement in edge computing networks,”IEEE Trans. Mobile Comput., vol. 24, no. 10, pp. 11046–11060, Oct. 2025. [7] A. Dimas, M. A. Clark, B. Li, K. Psounis, and A. P. Petropulu, “On radar privacy in shared spectrum scenarios,”in Proc. IEEE Int. Conf. Acoust. Speech Signal Process., Brighton, U.K., May 2019, pp. 7790–7794. [8] X. Li, Z


==============================================================================
FILE: [06]_UW-OCDM_for_Low-Altitude_UAV_Communication_and_Coo_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> 1 UW-OCDM for Low-Altitude UA V Communication and Cooperative Sensing Yi Tao, Zhen Gao, Senior Member, IEEE, Ziwei Wan, Yuezu Lv, Senior Member, IEEE, Hua Wang, Member, IEEE, Kaibin Huang, Fellow, IEEE, and Sheng Chen, Life Fellow, IEEE Abstract—Integrated sensing and communications (ISAC) is a key enabler for uncrewed aerial vehicles (UA Vs) in the low-altitude economy. This paper proposes an ISAC waveform that embeds a unique word (UW) into orthogonal chirp division multiplexing (OCDM), termed UW-OCDM, together with cor- responding communication reception and cooperative sensing schemes for high-mobility UA V scenarios. For communication, the embedded UW enables timing synchro

[ABSTRACT]
Integrated sensing and communications (ISAC) is a key enabler for uncrewed aerial vehicles (UA Vs) in the low-altitude economy. This paper proposes an ISAC waveform that embeds a unique word (UW) into orthogonal chirp division multiplexing (OCDM), termed UW-OCDM, together with cor- responding communication reception and cooperative sensing schemes for high-mobility UA V scenarios. For communication, the embedded UW enables timing synchronization and Doppler estimation and compensation without requiring a separate synchronization sequence. A sparse spatio-temporal channel estimation method exploits the common channel support across multiple receive antennas and consecutive UW observations to support reliable data demodulation. For sensing, the de- terministic UW serves as a shared prior that allows dis- tributed base stations to construct sensing dictionaries locally without exchanging random payload symbols in real time. A hierarchical multi-target detection and tracking algorithm integrates direct-path interference suppression, kinematic pre- diction, multi-candidate screening, off-grid refinement, residual verification, and successive interference cancellation for robust localization with reduced search complexity. Simulation results demonstrate reliable communication and localization in highly dynamic UA V scenarios, while the proposed framework retains low-complexity frequency-domain equalization and reduces transmit-reference sharing overhead and multi-static localiza- tion complexity.

[HEADINGS]
I. Introduction
  A. Contributions
II. System Model
  A. Doubly Selective MIMO Ground-to-Air Channel Mod-
  B. Multi-Static Cooperative Sensing Model
III. Proposed UW-OCDM ISAC Waveform
  A. OCDM Preliminaries
  B. Proposed UW-OCDM Waveform Design
  C. Implementation Considerations
IV. UW-Assisted Receiver Processing
  A. UW-Assisted Timing Synchronization
  B. UW-Assisted Doppler Mitigation
  C. MMV-OMP-Based Joint Channel Estimation
  D. Frequency-Domain Equalization and Data Demodula-
V. Multi-Static UA V Sensing and Localization
  A. Sensing Dictionary and Direct-Path Suppression
  B. Iterative Coarse-to-Fine Multi-Target Localization
  C. Computational Complexity Analysis
VI. Simulation Results
  A. UA V Communication Performance Evaluation
  B. UA V Localization Performance Evaluation
VII. Conclusion

[CONTRIBUTION]
ing multi-static sensing may require additional signaling for consistent reference reconstruction [34]. In contrast, the deterministic UW is known a priori and locally reconstructible at all BSs, enabling lightweight cooperative localization without exchanging instantaneous payload symbols [35]. A. Contributions To provide reliable communication and high-precision sensing for low-altitude networks, we propose a UW- OCDM ISAC framework. The UW supports synchroniza- tion, Doppler compensation, and CE for communication reception, while serving as a deterministic shared reference for multi-static cooperative sensing with reduced transmit- reference sharing overhead. The main contributions are summarized as follows. • UW-OCDM ISAC Waveform Design: For UA V net- works, we propose a novel ISAC waveform by em- bedding a deterministic UW sequence into OCDM symbols. Owing to its quadratic-phase chirp struc- ture, OCDM provides improved Doppler robustness over conventional OFDM in high-mobility channels. Meanwhile, the deterministic UW serves as a shared signal reference that can be reused across multiple communication and sensing operations within the proposed framework. • UW-Assisted Time Synchronization, Doppler Com- pensation, CE, and FDE: Building on the proposed waveform, we develop a UA V receiver framework to overcome severe doubly-selective fading. The UW first enables timing syn || ow-altitude networks, we propose a UW- OCDM ISAC framework. The UW supports synchroniza- tion, Doppler compensation, and CE for communication reception, while serving as a deterministic shared reference for multi-static cooperative sensing with reduced transmit- reference sharing overhead. The main contributions are summarized as follows. • UW-OCDM ISAC Waveform Design: For UA V net- works, we propose a novel ISAC waveform by em- bedding a deterministic UW sequence into OCDM symbols. Owing to its quadratic-phase chirp struc- ture, OCDM provides improved Doppler robustness over conventional OFDM in high-mobility channels. Meanwhile, the deterministic UW serves as a shared signal reference that can be reused across multiple communication and sensing operations within the proposed framework. • UW-Assisted Time Synchronization, Doppler Com- pensation, CE, and FDE: Building on the proposed waveform, we develop a UA V receiver framework to overcome severe doubly-selective fading. The UW first enables timing synchronization via sliding cross- correlation. The phase differences between sepa- rated ISI-free UW segments are then jointly ex- ploited to estimate and compensate for the dominant Doppler shift, completing the time-frequency align- ment. Furthermore, by exploiting the spatio-temporal (ST) joint sparsity of multiple-input multiple-output (MIMO) GA channels, we formulate a multi

[CONCLUSION]
This paper proposed a UW-OCDM ISAC framework for low-altitude UA V networks, jointly supporting high- mobility communication and multi-target sensing. At the waveform level, UW embedding established the circular convolution structure required for low-complexity FDE, while the quadratic phase rotation of OCDM enhanced Doppler resilience and mitigated the repetitive correlation ambiguity of UW-OFDM. Additionally, the known UW supported time synchronization, Doppler estimation and compensation, and sparse ST CE. For cooperative sensing, the UW was also utilized for multi-static UA V localization. Since the UW and system parameters were pre-stored at the cooperating BSs, sensing dictionaries were constructed locally without exchanging full payload data, thereby reducing transmit-reference sharing overhead. Combined with DPI suppression and hierarchical off-grid process- ing, the proposed localization method achieved robust multi-UA V localization under grid ambiguity and near- far interference. Numerical results demonstrated improved communication reliability and multi-target localization accuracy, confirming that the proposed UW-driven de- sign effectively supported both robust communication reception and cooperative sensing through their respective processing chains. Building on the demonstrated benefits of the UW-driven processing chain, future work will investigate its extension to other candidate waveforms and more general ISAC scenarios. Such extensions will require waveform-specific redesign of the UW embedding mechanism, parameter configuration, and receiver processing. The framework will also be further developed for distributed, multi-user, and learning-assisted ISAC systems under more practical synchronization, hardware, and environmental conditions. References [1] Y. Tao et al., “Intelligent Multimodal Multi-Sensor Fusion- Based UA V Identification, Localization, and Countermeasures for Safeguarding Low-Altitude Economy,” Chinese J. Electron., vol. 35, no. 6, pp. 1–13, 2026. [2] H. Liu et al., “Near-space communications: The last piece of 6G space–air–ground–sea integrated network puzzle,” Space Sci. Technol., vol. 4, p. 0176, 2024. [3] X. Liu et al., “


==============================================================================
FILE: [07]_LAMBDA_A_Low-Altitude_Multimodal_Base_Dataset_for_2026.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> LAMBDA: A Low-Altitude Multimodal Base Dataset for UA V Sensing and Communication Lin Zhou 1, Peichuan Rao 1, Chenshuo Zhang 1, Jianhua Mo 1,*, Shu Sun 1, Zhiyong Chen 1, and Meixia Tao 1,* Abstract Research on low-altitude integrated sensing and communication (ISAC) requires aligned multimodal data that jointly describe wireless propagation, visual appearance, unmanned aerial vehicle (UAV) motion, light detection and ranging (LiDAR) perception, and radar sensing under common trajectories and timestamps. To address this need, alow-altitudemultimodalbase dataset, named LAMBDA, is introduced. LAMBDA is characterized by high fidelity, modality diversity, scenario richness, and conf

[ABSTRACT]
Research on low-altitude integrated sensing and communication (ISAC) requires aligned multimodal data that jointly describe wireless propagation, visual appearance, unmanned aerial vehicle (UAV) motion, light detection and ranging (LiDAR) perception, and radar sensing under common trajectories and timestamps. To address this need, alow-altitudemultimodalbase dataset, named LAMBDA, is introduced. LAMBDA is characterized by high fidelity, modality diversity, scenario richness, and configuration flexibility. It is generated through a high-fidelity digital-twin pipeline with detailed scene geometry, refined material assignment, and electromag- netic modeling of UAVs. LAMBDA provides synchronized RGB images, depth maps, LiDAR point clouds, inertial measurement unit states, UAV poses, channel state information (CSI), and radar-synthesis resources across matched low-altitude operating conditions, shared coordinate systems, and synchronized frame indices. The dataset covers urban, suburban, and campus scenes, multi-UAV/multi-base-station settings, nighttime conditions, and sunny, rainy, snowy, and foggy weather variations. Its CSI and radar resources support user-defined antenna-array sizes, bandwidths, subcarrier spacings, chirp parameters, and plane-wave or spherical-wavefront channel synthesis. The reliability and usability of LAMBDA are assessed through quality con- trol, weather and multimodal visualization, and two UAV ISAC-related use cases: RGB-aided beam prediction and RGB–LiDAR-based UAV localization. Background & Summary The rapid proliferation of unmanned aerial vehicles (UAVs) has enabled a wide range of low-altitude applications, including autonomous delivery, emergency rescue, and infrastructure inspection [1,2]. Unlike conventional terrestrial systems, low-altitude UAV networks involve small aerial targets, rapidly varying air–ground channels, three-dimensional mobility, and strong sensitivity to sur- rounding geometry and weather conditions. Safe, reliable, and efficient UAV operation therefore requires not only robust wireless communication links but also accurate environmental perception and motion awareness under highly dynamic and complex propagatio

[HEADINGS]


[CONTRIBUTION]
ledgments The authors would like to thank Renjie He, Kejia Bian, Weitao Chen, Yuhe Huang, Lingbang Bu, Ziyan Wang, Xiang Li, Xiangwen Gu, and Xinyu Zhang for technical discussions and implementa- tion support for radar RCS modeling, wireless channel modeling, data collection, and validation. Author Contributions L.Z. conceived the dataset framework, implemented the generation and visualization pipeline, or- ganized the dataset, and drafted the manuscript. P.R. and C.Z. contributed to scene preparation, data collection, validation, and revision. J.M. defined the dataset scope, proposed the integrated tool chain for multimodal data generation, and provided technical guidance on data validation. M.T. defined the strategic scope of the dataset together with J.M., provided technical leadership, supervised the entire workflow, and proposed key methods for dataset validation. S.S. and Z.C. made suggestions on weather setup, material configuration, and scene construction. All authors discussed the results and reviewed the manuscript. Competing Interests The authors declare no competing interests. 20

[CONCLUSION]
(none found)


==============================================================================
FILE: [08]_Full-Dimensional_Beamforming_for_Multi-User_MIMO-O_2025.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> 1 Full-Dimensional Beamforming for Multi-User MIMO-OFDM ISAC for Low-Altitude UA V with Zero Sensing Resource Allocation Zhiwen Zhou, Y ong Zeng, Fellow, IEEE, Chunguo Li, Senior Member , IEEE, Fei Y ang, Y an Chen, Senior Member , IEEE, and Jingon Joung, Senior Member , IEEE Abstract—Low-altitude unmanned aerial vehicles (UA Vs) are expected to play an important role for low-altitude economy with a wide range of applications like precise agriculture, aerial delivery and surveillance. Integrated sensing and communi cation (ISAC) is a key technology to enable the large-scale deploym ent and routine usage of UA Vs by providing both communication an d sensing services efﬁciently. F

[ABSTRACT]
Low-altitude unmanned aerial vehicles (UA Vs) are expected to play an important role for low-altitude economy with a wide range of applications like precise agriculture, aerial delivery and surveillance. Integrated sensing and communi cation (ISAC) is a key technology to enable the large-scale deploym ent and routine usage of UA Vs by providing both communication an d sensing services efﬁciently. For UA V ISAC systems, as UA V often acts as both a communication user equipment (UE) and a sensin g target, traditional ISAC systems that usually allocate ded icated TF resources for sensing are inefﬁcient due to the severe deg ra- dation of communication spectral efﬁciency. To address thi s issue, in this paper , we propose a novel multiple-input multiple-o utput (MIMO) orthogonal frequency division multiplexing (OFDM) - based ISAC framework for UA Vs that eliminates the need for ded- icated sensing TF resources, achieving zero TF sensing over head. By designing the transmit beamforming to meet the require- ments for both communication and sensing tasks, our propose d approach enables the communication TF resources to be fully reused for sensing, thereby enhancing both the communicati on sum rate and the sensing performance in terms of resolution, unambiguous range, and accuracy. Additionally, we introdu ce a low-complexity target searching beamforming algorithm a nd a two-stage super-resolution sensing algorithm, which ens ure efﬁcient implementation. Simulation results demonstrate that the proposed MIMO-OFDM-ISAC framework not only improves the communication sum rate but also outperforms traditional IS AC systems in sensing performance, making it a promising solut ion for future ISAC systems to support low-altitude UA Vs.

[HEADINGS]
I. I NTRODUCTION
  J. Joung is with the School of Electrical and Electronics En-
II. S YSTEM MODEL
III. D EDICATED VERSUS ZERO SENSING RESOURCE
  A. Dedicated Sensing TF Resource Allocation
  B. Zero Sensing TF Resource Allocation
IV. B EAMFORMING DESIGN
  A. T arget Searching
  B. T arget Tracking
V. S ENSING ALGORITHM
  A. Spatial Domain Denoising
  B. Angle Sensing
  C. Delay-Doppler Sensing
VI. S IMULATION RESULTS
  A. Beamforming Design
  B. Denoising
  C. Sensing Performance
  D. Communication Performance
VII. C ONCLUSION

[CONTRIBUTION]
e beamforming algorithm and a tw o- stage super-resolution sensing algorithm. Unlike traditi onal ISAC systems, which sacriﬁce communication resources for sensing, our proposed method leverages the full potential o f the available resources, achieving superior performance i n both domains. The main contributions of this paper are as follows: • Zero Sensing Overhead: We propose a novel OFDM- ISAC framework tailored for low-altitude UA V appli- cations that eliminates the need for dedicated sensing TF resources, thereby maximizing the communication throughput while improving sensing performance. • Beamforming Design: We develop a transmit beamform- ing strategy that ensures both communication quality and sensing performance. The beamforming vectors are de- signed to minimize the transmit power while meeting the requirements for communication and sensing tasks. Fur- thermore, we introduce a closed-form and optimization- free beamforming algorithm for the searching stage, enabling low-complexity implementation. • Sensing Algorithms: To address the unique challenges of ISAC for UA Vs, we propose a low-complexity two-stage super-resolution sensing algorithm. In the ﬁrst stage, 2D angle estimation is performed using the multiple signal classiﬁcation (MUSIC) algorithm to achieve high angular resolution. In the second stage, 2D delay-Doppler estimation is conducted for each estimated sp

[CONCLUSION]
(none found)


==============================================================================
FILE: [10]_Ray_Antenna_Array_Achieves_Uniform_Angular_Resolut_2025.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> arXiv:2505.10306v1 [eess.SP] 15 May 2025 1 Ray Antenna Array Achieves Uniform Angular Resolution Cost-Effectively for Low-Altitude UA V Swarm ISAC Haoyu Jiang and Yong Zeng, Fellow, IEEE Abstract—Ray antenna array (RAA) is a novel multi-antenna architecture comprising massive low-cost antenna elements and a few radio-frequency (RF) chains. The antenna elements are arranged in a novel ray-like structure, where each ray corre- sponds to a simple uniform linear array (sULA) with deliberately designed orientation and all its antenna elements are directly connected. By further designing a ray selection network (RSN), appropriate sULAs are selected to connect to the RF chains for furt

[ABSTRACT]
Ray antenna array (RAA) is a novel multi-antenna architecture comprising massive low-cost antenna elements and a few radio-frequency (RF) chains. The antenna elements are arranged in a novel ray-like structure, where each ray corre- sponds to a simple uniform linear array (sULA) with deliberately designed orientation and all its antenna elements are directly connected. By further designing a ray selection network (RSN), appropriate sULAs are selected to connect to the RF chains for further baseband processing. Compared to the classic hy- brid analog/digital beamforming based on conventional antenna arrays, RAA has three appealing advantages: (i) dramatically reduced hardware cost since no phase shifters are needed; (ii) enhanced beamforming gain as antenna elements with higher directivity can be used; (iii) uniform angular resolution across all signal directions. Such benefits make RAA especially appealing for integrated sensing and communication (ISAC), particularly for low-altitude unmanned aerial vehicle (UA V) swarm ISAC, where high-mobility aerial targets may easily move away from the boresight of conventional antenna arrays, causing severe communication and sensing performance degradation. Therefore, this paper studies RAA-based ISAC for low-altitude UA V swarm systems. First, we establish an input-output mathematical model for RAA-based UA V ISAC and rigorously show that RAA achieves uniform angular resolution for all directions through beam pattern analysis. Besides, we design the RAA orientation and RSN to fully reap its advantages. Furthermore, RAA-based ISAC with orthogonal frequency division multiplexing (OFDM) for UA V swarm is studied, and efficient algorithm is proposed for sensing target parameter estimation. Extensive simulation results are provided to demonstrate the significant performance improvement by RAA system over the conventional antenna arrays, in terms of sensing angular resolution and communication spectral efficiency, highlighting the great potential of the novel RAA system to meet the growing demands of low-altitude UA V ISAC.

[HEADINGS]
I. I NTRODUCTION
II. S YSTEM MODEL
III. R AY ANTENNA ARRAY
IV. RAA VS CONVENTIONAL ULA
  A. Beam Pattern and Angular Resolution of RAA
  B. Beam Pattern and Angular Resolution of Conventional
V. S ENSING ALGORITHM FOR RAA- BASED OFDM-ISAC
  A. RAA-based OFDM-ISAC
  B. Sensing Algorithm Design
VI. S IMULATION RESULTS
VII. C ONCLUSION

[CONTRIBUTION]
ency systems like mmWave or THz systems where the signal wavelengths are very small. Motivated by the appealing advantages of RAA mentioned above and to fully reap its uniform angular resolution charac- teristic, in this paper we propose to use RAA for low-altitude UA V swarm ISAC systems. The main contributions of this paper are summarized as follows: • First, we investigate the novel RAA architecture for low- altitude UA V swarm ISAC systems. The input-output communication and sensing signal models are derived for the RAA-based UA V ISAC system. Besides, by analyzing the beam pattern of RAA, we rigorously show that RAA can achieve uniform angular resolution across all signal directions, which is strictly better than the conventional ULA that achieves equal array gain. In particular, different from ULA that suffers from poor angular resolution when the user/target is far away from the array boresight, RAA can maintain its high resolution ability in all directions. Besides, we also show that with the same array gain, since each sULA is only responsible for a smaller portion of the angular range, RAA can achieve higher beamforming gain than the conventional ULA since it can use antenna elements with higher directivity, benefiting both communication and sensing. • Next, based on the beam pattern analysis, we design the orientation of each sULA and the RSN to fully reap the advant

[CONCLUSION]
(none found)


==============================================================================
FILE: [11]_Cooperative_Sensing_and_Communication_Beamforming_2025.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> arXiv:2506.20244v1 [eess.SY] 25 Jun 2025 Cooperative Sensing and Communication Beamforming Design for Low-Altitude Economy Fangzhi Li, Zhichu Ren, Cunhua Pan, Hong Ren, Jing Jin, Qixing Wang, and Jiangzhou Wang Abstract—To empower the low-altitude economy with high- accuracy sensing and high-rate communication, this paper proposes a cooperative integrated sensing and communication (ISAC) framework for aerial-ground networks. In the proposed system, the ground base stations (BSs) cooperatively serve the unmanned aerial vehicles (UA Vs), which are equipped for either joint communication and sensing or sensing-only operations. The BSs employ coordinated beamforming to simultaneousl

[ABSTRACT]
To empower the low-altitude economy with high- accuracy sensing and high-rate communication, this paper proposes a cooperative integrated sensing and communication (ISAC) framework for aerial-ground networks. In the proposed system, the ground base stations (BSs) cooperatively serve the unmanned aerial vehicles (UA Vs), which are equipped for either joint communication and sensing or sensing-only operations. The BSs employ coordinated beamforming to simultaneously transmit communication and sensing signals, while the UA Vs execute their missions. To maximize the weighted sum rate under the sensing signal-to-interference-plus-noise ratio (SINR) con- straints, we jointly optimize the transmit beamforming, receive filtering, and UA V trajectory. The resulting non-convex problem is solved using an alternating optimization framework incor- porating semidefinite relaxation (SDR) and successive convex approximation (SCA). Simulation results demonstrate that the proposed joint design achieves higher communication throughput while ensuring required sensing robustness. Additionally, the sensing SINR threshold and the UA V altitude have a significant impact on the trajectory design, highlighting the necessity of adaptive deployment strategies in practical applications.

[HEADINGS]
I. I NTRODUCTION
II. S YSTEM MODEL
  A. Communication Model
  B. Sensing Model
  C. Promblem F ormulation
III. P ROPOSED SOLUTION
  A. Problem Reformulation
  B. Transmit Beamforming Optimization
  C. Receive Filter Optimization
  D. UA V Trajectory Optimization
IV. N UMERICAL RESULTS
V. C ONCLUSION

[CONTRIBUTION]
,t[n])H and Wr m,k[n] = wr m,k[n](wr j,t[n])H, where Wc m,k[n]⪰ 0, Wr m,k[n]⪰ 0, and rank(Wc m,k[n]) = 1, the transmit signal covariance matrix Xj[n] can be equiva- lently expressed as Xj[n] = X t∈Kcs Wc j,t[n] + X t∈K Wr j,t[n], (25) where Xj[n]⪰ 0 and each term in the summation corresponds to the contribution from either communication or sensing beamforming signals. With these reformulations, problem (P1) can be equivalently transformed into the following problem (P2): (P2) : max {Wc m,k[n],Wr m,k[n],uj,k[n],qk[n]} X n∈N X k∈K ωk ¯Rk[n], (26a) s.t. X k∈Kcs tr(Wc m,k[n]) + X k∈K tr(Wr m,k[n])≤Pmax,∀m,n, (26b) rank(Wc m,k[n]) = 1,∀m,k,n, (26c) (21b), (21d), (21e), (21f), (21g) . To solve (P2), we adopt the Alternating Optimization (AO)- based algorithm, iteratively optimizing one set of variables while fixing the others. B. Transmit Beamforming Optimization In this section, we propose an efficient algorithm to address problem (P2), focusing on optimizing the communication and sensing beamforming matrices Wc m,k[n] and Wr m,k[n]. The optimization is performed under fixed filter designs uj,k[n] and UA V trajectoriesqk[n]. By carefully analyzing the structure of the problem, it can be seen that optimizing the beamforming is equivalent to solving the following problem (P3): (P3) : max {Wc m,k[n],Wr m,k[n]} X n∈N R[n] s.t. (21b), (26b), (26c). Constraint (26b), which represents the

[CONCLUSION]
(none found)


==============================================================================
FILE: [12]_Digital_Twin_Assisted_Beamforming_Design_for_Integ_2024.txt
==============================================================================

[HEADER]
<<<PAGE 1>>> Digital Twin Assisted Beamforming Design for Integrated Sensing and Communication Systems Shuaifeng Jiang and Ahmed Alkhateeb School of Electrical, Computer, and Energy Engineering, Arizona State University Emails:{s.jiang, alkhateeb}@asu.edu Abstract—This paper explores a novel research direction where a digital twin is leveraged to assist the beamforming design for an integrated sensing and communication (ISAC) system. In this setup, a base station designs joint communication and sensing beamforming to serve the communication user and detect the sensing target concurrently. Utilizing the electromagnetic (EM) 3D model of the environment and ray tracing, the digital twin can pro

[ABSTRACT]
This paper explores a novel research direction where a digital twin is leveraged to assist the beamforming design for an integrated sensing and communication (ISAC) system. In this setup, a base station designs joint communication and sensing beamforming to serve the communication user and detect the sensing target concurrently. Utilizing the electromagnetic (EM) 3D model of the environment and ray tracing, the digital twin can provide various information, e.g., propagation path parameters and wireless channels, to aid communication and sensing systems. More specifically, our digital twin-based beamforming design first leverages the environment EM 3D model and ray tracing to (i) predict the directions of the line-of-sight (LoS) and non-line-of- sight (NLoS) sensing channel paths and (ii) identify the dominant one among these sensing channel paths. Then, to optimize the joint sensing and communication beam, we maximize the sensing signal- to-noise ratio (SNR) on the dominant sensing channel component while satisfying a minimum communication signal-to-interference- plus-noise ratio (SINR) requirement. Simulation results show that the proposed digital twin-assisted beamforming design achieves near-optimal target sensing SNR in both LoS and NLoS dominant areas, while ensuring the required SINR for the communication user. This highlights the potential of leveraging digital twins to assist ISAC systems.

[HEADINGS]
I. I NTRODUCTION
II. S YSTEM MODEL
  A. Signal Model
  B. Communication Model
III. P ROBLEM FORMULATION
IV. B ASELINE SOLUTIONS
  A. ISAC with Full Sensing Channel
  B. ISAC with LoS Sensing Direction
  B. Sensing Though the Direction of the Strong Partial Path
VI. S IMULATION RESULTS
  A. Scenario Setup
  B. Data Generation
  C. Evaluation Results
VII. C ONCLUSION

[CONTRIBUTION]
twin-assisted beamforming approach for ISAC systems. In particular, the digital twin is leveraged to predict the directions and partial channel gains of both LoS and NLoS sensing channel paths. This sensing channel information is then used to guide the design of the efficient ISAC beamforming. The contribution of this paper is threefold. • We proposed to leverage digital twins to infer information about the wireless sensing channel, thereby assisting the operation of ISAC systems. • We first develop a joint communication and sensing beamforming design that leverages the dominant NLoS direction of the sensing target predicted by the digital twin, which achieves high sensing performance for NLoS sensing directions. • We then propose a joint communication and sensing beam- forming design that utilizes the partial channel information predicted by the digital twin, which can adapt to both LoS and NLoS sensing directions. We evaluate the proposed digital twin-aided ISAC beamform- arXiv:2412.07180v1 [eess.SP] 10 Dec 2024 <<<PAGE 2>>> Sensing beam BS Dominant sensing path Sub-dominant sensing path Sensing target Digital Replica Comm  beam Dominant sensing direction Sensing target postion Blockage Fig. 1. This figure presents the key idea of leveraging the digital twin to design the joint communication and sensing beamforming. The digital twin can provide partial channel in

[CONCLUSION]
(none found)
