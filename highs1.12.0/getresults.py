import os
import re
import sys
import numpy as np
import gzip
import csv

# constants for statistic
INF = 1e20
SH = 1
SH_INT= 1
TIMELIMIT = 7200

SOLFILE_OPT = '=opt='
SOLFILE_UBD = '=ubd='
SOLFILE_INF = '=inf='

READ_UBD = 'Unbounded'
READ_INF = 'Infeasible'
READ_OPT = 'Optimal'
READ_TLIM = 'Time limit reached'
READ_NOT_COLLECT = 'Not Collected'

STATUS_SOLVED = 'solved'
STATUS_TIMEOUT = 'time'
STATUS_MISMATCH = 'mismatch'
STATUS_FAIL = 'fail'

# options
NODE_BOTH_SOLVED = True
RowX = [0, 1, 10, 100, 1000]
settingStack = {}
problemStack = {}
ErrorList = []
excludeFiles = []


def process_folder(folder1, folder2):
    settingStack = {}
    problemStack = {}
    ErrorList = []
    excludeFiles = []


    fileList1 = os.listdir(folder1)
    fileList1 = [os.path.join(folder1, file) for file in fileList1]

    fileList2 = os.listdir(folder2)
    fileList2 = [os.path.join(folder2, file) for file in fileList2]
    
    fulllist = fileList1 + fileList2
    fulllist.sort()

    for filename in fulllist:
        if filename.endswith('.out'):
            result = parse_out_file(filename)
            if result:
                analyze_instance(result, problemStack)
                

    # exclude those files
    affectedInstance = []
    keylist = list(problemStack.keys())
    for name in keylist:
        # if len(problemStack[name]) != 2 or name == 'dws008-01.5' or name == 'traininstance2.4' or name == 'ex10.1':
        if len(problemStack[name]) != 2 or name == 'dws008-01.5' or name == 'traininstance2.4':
        # if len(problemStack[name]) != 2 or name == 'dws008-01.5' or name == 'traininstance2.4' or name == 'neos-3988577-wolgan.3' or name == 'neos-3988577-wolgan.4' or name == 'rail01.1' or name == 'rail01.2':
            problemStack.pop(name)
        else:
            setting0 = problemStack[name][0]['setting']
            setting1 = problemStack[name][1]['setting']
            if isProblemInfluenced(problemStack, name):
                if problemStack[name][0]['status'] == STATUS_SOLVED or problemStack[name][1]['status'] == STATUS_SOLVED:
                    affectedInstance.append(name)
            if setting0 in settingStack:
                settingStack[setting0].append(problemStack[name][0])
            else:
                settingStack[setting0] = [problemStack[name][0]]
            if setting1 in settingStack:
                settingStack[setting1].append(problemStack[name][1])
            else:
                settingStack[setting1] = [problemStack[name][1]]

    settingKeys = list(settingStack.keys())
    # calculate average
    averageItem = ['total_time', 'probing_time', 'nodes', 'implicationsFirstRound', 'fixFirstRound', 'presolved_row', 'presolved_col', 'presolved_nnz']
    solvedItem = {key : [0 for _ in RowX] for key in settingKeys}
    solvedItemAffected = {key : [0 for _ in RowX] for key in settingKeys}
    instanceCollect = [[] for _ in RowX]
    instanceCollectAffected = [[] for _ in RowX]

    for name in problemStack.keys():
        haveSolved = False
        haveMismatch = False
        maxTime = 0
        settingSolved = {}
        if len(problemStack[name]) != 2:
            continue
        for info in problemStack[name]:
            maxTime = max(maxTime, info['total_time'])
            if info['status'] == STATUS_MISMATCH or info['status'] == STATUS_FAIL:
                haveMismatch = True
            elif info['status'] == STATUS_SOLVED:
                haveSolved = True
                settingSolved[info['setting']] = 1
        if not haveMismatch and haveSolved:
            for i in range(len(RowX)):
                if maxTime >= RowX[i]:
                    instanceCollect[i].append(name)

    for name in affectedInstance:
        haveSolved = False
        haveMismatch = False
        maxTime = 0
        settingSolved = {}
        if len(problemStack[name]) != 2:
            continue
        for info in problemStack[name]:
            maxTime = max(maxTime, info['total_time'])
            if info['status'] == STATUS_MISMATCH or info['status'] == STATUS_FAIL:
                haveMismatch = True
            elif info['status'] == STATUS_SOLVED:
                haveSolved = True
                settingSolved[info['setting']] = 1
        if not haveMismatch and haveSolved:
            for i in range(len(RowX)):
                if maxTime >= RowX[i]:
                    instanceCollectAffected[i].append(name)

    settingCollect = {x : {} for x in averageItem}
    settingCollectAffected = {x : {} for x in averageItem}
    for item in averageItem:
        settingCollect[item] = {y : [0.0 for _ in RowX] for y in settingKeys}
        settingCollectAffected[item] = {y : [0.0 for _ in RowX] for y in settingKeys}

    for i in range(len(RowX)):
        problemlist = instanceCollect[i]
        nProblem = len(instanceCollect[i])
        nNodeInclude = 0
        if nProblem == 0:
            continue
        ## all instances
        for probname in problemlist:
            for info in problemStack[probname]:
                if info['status'] == STATUS_SOLVED:
                    solvedItem[info['setting']][i] += 1
                for item in averageItem:
                    if item == 'nodes' and NODE_BOTH_SOLVED:
                        solved1 = problemStack[probname][0]['status'] == STATUS_SOLVED
                        solved2 = problemStack[probname][1]['status'] == STATUS_SOLVED
                        if (not solved1) or (not solved2):
                            continue
                        nNodeInclude += 1
                    if item == 'total_time':
                        settingCollect[item][info['setting']][i] += np.log(max(info[item] + SH, 1))
                    else:
                        settingCollect[item][info['setting']][i] += np.log(max(info[item] + SH_INT, 1))
        for item in averageItem:
            for setting in settingKeys:
                if item == 'nodes' and NODE_BOTH_SOLVED:
                    tmpValue = settingCollect[item][setting][i] / (nNodeInclude/2)
                else:  
                    tmpValue = settingCollect[item][setting][i] / nProblem
                if item == 'total_time':
                    settingCollect[item][setting][i] = np.exp(tmpValue) - SH
                else:
                    settingCollect[item][setting][i] = np.exp(tmpValue) - SH_INT

        ## affected instances
        problemlist = instanceCollectAffected[i]
        nProblem = len(instanceCollectAffected[i])
        nNodeInclude = 0
        for probname in problemlist:
            for info in problemStack[probname]:
                if info['status'] == STATUS_SOLVED:
                    solvedItemAffected[info['setting']][i] += 1
                for item in averageItem:
                    if item == 'nodes' and NODE_BOTH_SOLVED:
                        solved1 = problemStack[probname][0]['status'] == STATUS_SOLVED
                        solved2 = problemStack[probname][1]['status'] == STATUS_SOLVED
                        if (not solved1) or (not solved2):
                            continue
                        nNodeInclude += 1
                    if item == 'total_time':
                        settingCollectAffected[item][info['setting']][i] += np.log(max(info[item] + SH, 1))
                    else:
                        settingCollectAffected[item][info['setting']][i] += np.log(max(info[item] + SH_INT, 1))
        for item in averageItem:
            for setting in settingKeys:
                if item == 'nodes' and NODE_BOTH_SOLVED:
                    tmpValue = settingCollectAffected[item][setting][i] / (nNodeInclude/2)
                else:
                    tmpValue = settingCollectAffected[item][setting][i] / nProblem
                if item == 'total_time':
                    settingCollectAffected[item][setting][i] = np.exp(tmpValue) - SH
                else:
                    settingCollectAffected[item][setting][i] = np.exp(tmpValue) - SH_INT
    if 'default' in settingKeys:
        compareSetting = 'default'
        if compareSetting == settingKeys[1]:
            settingKeys = settingKeys[::-1]
    elif '2013' in settingKeys:
        compareSetting = '2013'
        if compareSetting == settingKeys[1]:
            settingKeys = settingKeys[::-1]
    elif 'linear' in settingKeys:
        compareSetting = 'linear'
        if compareSetting == settingKeys[1]:
            settingKeys = settingKeys[::-1]
    else:
        compareSetting = settingKeys[0]

    ####################################    开始输出结果!    #####################################
    print("\n\n-------------------------------------   Result comparsion between *" + os.path.basename(folder1) + "* and *" + os.path.basename(folder2) + "*   -------------------------------------")
    # 开始输出结果!
    bigBlock = 20
    blockSize = 15
    newblock = bigBlock + bigBlock

    setting_name = os.path.basename(folder2)

    # 1. overall performance of solvers
    print("------------------------ 1. Overall Performance of Solvers ------------------------")
    print("\\begin{table}[htbp]")
    print("    \\renewcommand{\\arraystretch}{1.4}")
    print("    \\addtolength{\\tabcolsep}{-1pt}")
    print("    \\centering")
    print("    \\scriptsize")

    # 固定列数：Bracket + #Ins + settings*3 + Compare*2
    n_fixed_cols = 1 + 1 + len(settingKeys)*3 + 2
    tabular_def = "{|" + "r|" * n_fixed_cols + "}"
    tabular_def = tabular_def.replace("r|r|", "l|r|", 1)
    print(f"    \\begin{{tabular}}{{{tabular_def}}} \\hline")

    # 第一行表头：各 setting 占3列，Compare 占2列
    header_cols = ['', '']  # 前两个空位用于对齐 Bracket 和 #Ins
    for setting in settingKeys:
        header_cols.append(f"\\multicolumn{{3}}{{c|}}{{{setting}}}")
    header_cols.append("\\multicolumn{2}{c|}{Compare}")
    # 构建第一行，每个元素之间用 & 连接，末尾不加 &
    header_line = "    " + " & ".join(header_cols).rjust(blockSize * len(header_cols)) + " \\\\ \\hline"
    print(header_line)

    # 第二行表头：具体列名
    subheader_cols = ["Bracket", "\\tblIns"]
    for setting in settingKeys:
        subheader_cols.extend(["\\tblS", "\\tblT", "\\tblN"])
    subheader_cols.extend(["\\tblT", "\\tblN"])   # Compare 两列
    subheader_line = "    " + " & ".join([col.rjust(blockSize) for col in subheader_cols]) + " \\\\ \\hline"
    print(subheader_line)

    # 输出每个 bracket 的行（不含 affected 列）
    for i in range(len(RowX)):
        minTime = getItem(settingCollect, 'total_time', compareSetting, i)
        minNode = getItem(settingCollect, 'nodes', compareSetting, i)
        
        row_cols = []
        # 第一列 Bracket
        row_cols.append('$\\ge$ ' + format(int(RowX[i]), '4d'))
        # 第二列 #Ins
        row_cols.append(str(len(instanceCollect[i])))
        # 每个 setting 的三列： #S, T, N
        for setting in settingKeys:
            row_cols.append(format(int(getSolvedN(solvedItem, setting, i)), '5d'))
            row_cols.append(format(float(getItem(settingCollect, 'total_time', setting, i)), '10.2f'))
            row_cols.append(format(float(getItem(settingCollect, 'nodes', setting, i)), '10.2f'))
        # Compare 两列 (与 compareSetting 比较)
        for setting in settingKeys:
            if setting == compareSetting:
                continue
            if minTime == 0:
                row_cols.append('    --       ')
                row_cols.append('    --       ')
            else:
                row_cols.append(format(float(getItem(settingCollect, 'total_time', setting, i)/minTime), '10.2f'))
                row_cols.append(format(float(getItem(settingCollect, 'nodes', setting, i)/minNode), '10.2f'))
        # 拼接行，列之间用 &，末尾不加 &
        outputLine = "    " + " & ".join([col.center(blockSize - 1) for col in row_cols]) + " \\\\ \\hline"
        print(outputLine)

    # ------------------- 添加 affected 汇总行 -------------------
    i = 0   # 使用第一行（>0）的 affected 数据
    affected_instances = len(instanceCollectAffected[i])
    minTimeAffected = getItem(settingCollectAffected, 'total_time', compareSetting, i)
    minNodeAffected = getItem(settingCollectAffected, 'nodes', compareSetting, i)

    row_cols_affected = []
    row_cols_affected.append("      Affected")
    row_cols_affected.append(str(affected_instances))
   
    for setting in settingKeys:
        row_cols_affected.append(format(getSolvedN(solvedItemAffected, setting, i), '5d'))
        row_cols_affected.append(format(getItem(settingCollectAffected, 'total_time', setting, i), '10.2f'))
        row_cols_affected.append(format(getItem(settingCollectAffected, 'nodes', setting, i), '10.2f'))
    for setting in settingKeys:
        if setting == compareSetting:
            continue
        if minTimeAffected == 0:
            row_cols_affected.append('    --       ')
            row_cols_affected.append('    --       ')
        else:
            row_cols_affected.append(format(getItem(settingCollectAffected, 'total_time', setting, i) / minTimeAffected, '10.2f'))
            row_cols_affected.append(format(getItem(settingCollectAffected, 'nodes', setting, i)  / minNodeAffected, '10.2f'))

    outputLine_affected = "    " + " & ".join([col.center(blockSize - 1) for col in row_cols_affected]) + " \\\\ \\hline"
    print(outputLine_affected)

    # 结束表格
    print("    \\end{tabular}")
    print("    \\caption{<caption>}")
    print("    \\label{<label>}")
    print("\\end{table}")

    
    # # 2. Presolved Model Size 比较表格
    # print("\n\n------------------------ 2. Presolved Model Size ------------------------")
    # print("\\begin{table}[htbp]")
    # print("    \\renewcommand{\\arraystretch}{1.4}")
    # print("    \\addtolength{\\tabcolsep}{-1pt}")
    # print("    \\centering")
    # print("    \\scriptsize")

    # # 动态列数：Bracket(1) + #Ins(1) + len(settings)*4 + Compare(3)
    # n_cols = 1 + 1 + len(settingKeys)*4 + 3
    # tabular_def = "{|" + "r|" * n_cols + "}"
    # tabular_def = tabular_def.replace("r|r|", "l|r|", 1)
    # print(f"    \\begin{{tabular}}{{{tabular_def}}} \\hline")

    # # 第一行：每个 setting 占4列
    # header_cols = ['', '']  # Bracket, #Ins 占位
    # for setting in settingKeys:
    #     header_cols.append(f"\\multicolumn{{4}}{{c|}}{{{setting}}}")
    # header_cols.append("\\multicolumn{3}{c|}{Compare}")
    # header_line = "    " + " & ".join(header_cols) + " \\\\ \\hline"
    # print(header_line)

    # # 第二行：具体列名
    # subheader_cols = ["Bracket", "\\#Ins"]
    # for setting in settingKeys:
    #     subheader_cols.extend(["\\#S", "\\tblRow", "\\tblCol", "\\tblNnz"])
    # subheader_cols.extend(["\\tblRow", "\\tblCol", "\\tblNnz"])   # Compare 三列
    # subheader_line = "    " + " & ".join([col.rjust(12) for col in subheader_cols]) + " \\\\ \\hline"
    # print(subheader_line)

    # # 输出每个 bracket 的行
    # for i in range(len(RowX)):
    #     minRows = getItem(settingCollect, 'presolved_row', compareSetting, i)
    #     minCols = getItem(settingCollect, 'presolved_col', compareSetting, i)
    #     minNnz  = getItem(settingCollect, 'presolved_nnz', compareSetting, i)

    #     row_cols = []
    #     row_cols.append('$\\ge$ ' + format(int(RowX[i]), '4d'))          # Bracket
    #     row_cols.append(str(len(instanceCollect[i])))                    # #Ins
    #     for setting in settingKeys:
    #         row_cols.append(format(int(getSolvedN(solvedItem, setting, i)), '5d'))                     # #S
    #         row_cols.append(format(float(getItem(settingCollect, 'presolved_row', setting, i)), '10.2f'))  # Rows
    #         row_cols.append(format(float(getItem(settingCollect, 'presolved_col', setting, i)), '10.2f'))  # Cols
    #         row_cols.append(format(float(getItem(settingCollect, 'presolved_nnz', setting, i)), '10.2f'))  # Nnz
    #     # Compare 三列 (相对于 compareSetting)
    #     for setting in settingKeys:
    #         if setting == compareSetting:
    #             continue
    #         # 计算比率，防止除零
    #         if minRows == 0:
    #             row_cols.append("---")
    #         else:
    #             row_cols.append(format(getItem(settingCollect, 'presolved_row', setting, i) / minRows, '10.2f'))
    #         if minCols == 0:
    #             row_cols.append("---")
    #         else:
    #             row_cols.append(format(getItem(settingCollect, 'presolved_col', setting, i) / minCols, '10.2f'))
    #         if minNnz == 0:
    #             row_cols.append("---")
    #         else:
    #             row_cols.append(format(getItem(settingCollect, 'presolved_nnz', setting, i) / minNnz, '10.2f'))
    #     outputLine = "    " + " & ".join([col.center(12) for col in row_cols]) + " \\\\ \\hline"
    #     print(outputLine)

    # # Affected 汇总行
    # i = 0   # 以第一个门槛（≥0）的 affected 数据为准
    # affected_instances = len(instanceCollectAffected[i])
    # minRowsAff = getItem(settingCollectAffected, 'presolved_row', compareSetting, i)
    # minColsAff = getItem(settingCollectAffected, 'presolved_col', compareSetting, i)
    # minNnzAff  = getItem(settingCollectAffected, 'presolved_nnz', compareSetting, i)

    # row_aff = []
    # row_aff.append("    Affected")
    # row_aff.append(str(affected_instances))
    # for setting in settingKeys:
    #     row_aff.append(format(getSolvedN(solvedItemAffected, setting, i), '5d'))
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_row', setting, i), '10.2f'))
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_col', setting, i), '10.2f'))
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_nnz', setting, i), '10.2f'))
    # for setting in settingKeys:
    #     if setting == compareSetting:
    #         continue
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_row', setting, i) / minRowsAff if minRowsAff != 0 else 0, '10.2f'))
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_col', setting, i) / minColsAff if minColsAff != 0 else 0, '10.2f'))
    #     row_aff.append(format(getItem(settingCollectAffected, 'presolved_nnz', setting, i) / minNnzAff if minNnzAff != 0 else 0, '10.2f'))
    # output_aff = "    " + " & ".join([col.center(12) for col in row_aff]) + " \\\\ \\hline"
    # print(output_aff)

    # print("    \\end{tabular}")
    # print("    \\caption{<caption>}")
    # print("    \\label{<label>}")
    # print("\\end{table}")


    # # 2. probing time, implications and variable fixings
    # if 1:
    #     return
    # print("------------------------ 2. Probing time, number of implications and number of variable fixings ------------------------")
    # print("\\begin{table}[htbp]")
    # print("    \\centering")
    # print("    \\begin{tabular}{|l|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|} \hline")

    # nProblems = len(problemStack.keys())
    # # header = '              |    '
    # header = '    ' + '&'.rjust(blockSize)
    # for setting in settingKeys:
    #     header += ('\multicolumn{3}{c|}{' + setting + '}  &').rjust(blockSize * 3)
    # header += "\\multicolumn{3}{c|}{Compare} &".rjust(blockSize * 3) + "\\multicolumn{3}{c|}{Affected}     ".rjust(blockSize * 3)
    # header += " \\\\ \hline"

    # print(header)
    # header = "  Bracket   &".rjust(blockSize)
    # for setting in settingKeys:
    #     header += "\\#Fix   &".rjust(blockSize) + "\\#Impl   &".rjust(blockSize) + "T\_\{probing\}   &".rjust(blockSize)
    # header += "\\#Fix   &".rjust(blockSize) + "\\#Impl   &".rjust(blockSize) + "T\_\{probing\}   &".rjust(blockSize)
    # header += " \\\\ \hline"
    # print(header)

    # for i in range(len(RowX)):
    #     ## all instances
    #     minFix = getItem(settingCollect, 'fixFirstRound', compareSetting, i)
    #     minImpl = getItem(settingCollect, 'implicationsFirstRound', compareSetting, i)
    #     minPTime = getItem(settingCollect, 'probing_time', compareSetting, i)
    #     outputLine = '$\\ge$' + (format(int(RowX[i]), '4d')).center(blockSize - 1) + '&'
    #     for setting in settingKeys:
    #         outputLine += format(float(getItem(settingCollect, 'fixFirstRound', setting, i)), '10.2f').ljust(blockSize - 1) + '&'
    #         outputLine += format(float(getItem(settingCollect, 'implicationsFirstRound', setting, i)), '10.2f').ljust(blockSize - 1) + '&'
    #         outputLine += format(float(getItem(settingCollect, 'probing_time', setting, i)), '10.2f').ljust(blockSize - 1) + '&'
    #     for setting in settingKeys:
    #         if setting == compareSetting:
    #             continue
    #         if minPTime == 0:
    #             outputLine += '    --       '.rjust(blockSize - 1) + '&'
    #             outputLine += '    --       '.rjust(blockSize - 1) + '&'
    #         else:
    #             outputLine += format(float(getItem(settingCollect, 'fixFirstRound', setting, i) / minFix), '10.2f').center(blockSize - 1) + '&'
    #             outputLine += format(float(getItem(settingCollect, 'implicationsFirstRound', setting, i) / minImpl), '10.2f').center(blockSize - 1) + '&'
    #             outputLine += format(float(getItem(settingCollect, 'probing_time', setting, i) / minPTime), '10.2f').center(blockSize - 1) + '&'
    #     ## affected instances
    #     minFixAffected = getItem(settingCollectAffected, 'fixFirstRound', compareSetting, i)
    #     minImplAffected = getItem(settingCollectAffected, 'implicationsFirstRound', compareSetting, i)
    #     minPtimeAffected = getItem(settingCollectAffected, 'probing_time', compareSetting, i)
    #     outputLine += format(float(getItem(settingCollectAffected, 'fixFirstRound', setting, i)/minFixAffected), '10.2f').center(blockSize - 1) + '&'
    #     outputLine += format(float(getItem(settingCollectAffected, 'implicationsFirstRound', setting, i)/minImplAffected), '10.2f').center(blockSize - 1) + '&'
    #     outputLine += format(float(getItem(settingCollectAffected, 'probing_time', setting, i)/minPtimeAffected), '10.2f').center(blockSize)
    #     outputLine += " \\\\ \hline"
    #     print(outputLine)

    # print("    \\end{tabular}")
    # print("    \\caption{<caption>}")
    # print("    \\label{<label>}")
    # print("\\end{table}")


def parse_out_file(file_path):
    tmpPath = file_path
    nameArrary = tmpPath.split(".")
    probname = nameArrary[1]
    seed = nameArrary[2]
    setting = nameArrary[4]
    timelimit = int(nameArrary[5][:-1])
    TIMELIMIT = timelimit

    status = READ_NOT_COLLECT
    primal_bound = INF
    dual_bound = -INF
    gap = INF
    sol_Obj = INF
    total_time = 0
    presolve_time = 0
    postsolve_time = 0
    probing_time = 0
    nodes = 0
    implicationsFirstRound = 0
    fixFirstRound = 0
    lp_iterations = 0
    presolved_row = 0
    presolved_col = 0
    presolved_nnz = 0
    binary_vars = 0
    integer_vars = 0
    implied_int_vars = 0
    continuous_vars = 0

    conf = 0
    V1 = 0
    V2 = 0
    prow = 0

    with open(tmpPath, 'rt', encoding='utf-8') as f:
        content = f.read()
    content += "\n\n\n"

    # 匹配 conf
    cliques_match = re.search(r'Total cliques added:\s*(\d+)', content)
    if cliques_match:
        conf = int(cliques_match.group(1))
    
    # 匹配 V2
    variables_changed_match = re.search(r'Nonbinary variables tightened:\s*(\d+)', content)
    if variables_changed_match:
        V2 = int(variables_changed_match.group(1))
    
    # 匹配 V1
    binary_fixed_match = re.search(r'Binary variables fixed:\s*(\d+)', content)
    if binary_fixed_match:
        V1 = int(binary_fixed_match.group(1))

    # 匹配 prow
    presolve_section_match = re.search(r'Presolving model(.*)', content, re.DOTALL)
    if presolve_section_match:
        presolve_text = presolve_section_match.group(1)
        # 匹配所有行的 rows 数字
        rows_matches = re.findall(r'(\d+)\s+rows,', presolve_text)
        if rows_matches:
            prow = int(rows_matches[-1])  # 取最后一个 rows 数字

    # presolved model size
    rowinfo = re.search(r'\s*(\d+) rows\n', content)
    presolved_row = int(rowinfo.group(1)) if rowinfo else 0
    colinfo = re.search(r'\s*(\d+) cols \((\d+) binary, (\d+) integer, (\d+) implied int., (\d+) continuous, (\d+) domain fixed\)\n', content)
    presolved_col = int(colinfo.group(1)) if colinfo else 0
    binary_vars = int(colinfo.group(2)) if colinfo else 0
    integer_vars = int(colinfo.group(3)) if colinfo else 0
    implied_int_vars = int(colinfo.group(4)) if colinfo else 0
    continuous_vars = int(colinfo.group(5)) if colinfo else 0
    nnzinfo = re.search(r'\s*(\d+) nonzeros\n', content)
    presolved_nnz = int(nnzinfo.group(1)) if nnzinfo else 0
    
    goError = False;
    # 使用正则表达式提取 Solving report 部分
    solving_report_pattern = r'Solving report\n(.*?)\n\n'
    solving_report_match = re.search(solving_report_pattern, content, re.DOTALL)
    if not solving_report_match:
        goError = True
    if not goError:
        solving_report = solving_report_match.group(1)
        statusContent = re.search(r'  Status\s+([^\n]+)', solving_report)
        if statusContent == None:
            goError = True;
        else:
            status = statusContent.group(1).strip()
    # if not goError:
    #     implicationsFirstRound = re.search(r'\s*(\d*) \(First-Round-Implications\)\n', solving_report)
    #     implicationsFirstRound = int(implicationsFirstRound.group(1)) if implicationsFirstRound else 0
    #     fixFirstRound = re.search(r'  Implication & Fix\s+(\d+)', solving_report)
    #     fixFirstRound = int(fixFirstRound.group(1)) if fixFirstRound else 0

    #     gapPattern = re.compile(r'\s*Gap\s+((inf|-inf)|[\d\.%]+)', re.IGNORECASE)
    #     gapMatch = gapPattern.search(solving_report)
    #     if gapMatch == None:
    #         goError = True
    #     else:
    #         gap_str = gapMatch.group(1).strip()
    #         # 检查是否为 inf 或 -inf
    #         if gap_str.lower() == 'inf':
    #             gap = INF
    #         elif gap_str.lower() == '-inf':
    #             gap = -INF            
    #         # 如果不是 inf，尝试将带百分号的字符串转换为浮点数
    #         try:
    #             # 去掉百分号
    #             gap_str = gap_str.replace('%', '')
    #             gap = float(gap_str)
    #         except ValueError:
    #             # 如果无法转换为浮点数，返回原始字符串
    #             print("Gap error!", file_path)
    if not goError:
        primal_bound_pattern = re.compile(r'  Primal bound\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|inf|-inf)', re.IGNORECASE)
        dual_bound_pattern = re.compile(r'  Dual bound\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|inf|-inf)', re.IGNORECASE)

        primalboundmatch = primal_bound_pattern.search(solving_report)
        if primalboundmatch:
            # 提取并返回 Primal bound 值
            primal_bound = primalboundmatch.group(1).strip()
            if primal_bound == 'inf':
                primal_bound = INF  # 替换为 1e20
            elif primal_bound == '-inf':
                primal_bound = -INF  # 替换为 -1e20
            else:
                primal_bound = float(primal_bound)
        else:
            goError = True;
        
        dualboundmatch = dual_bound_pattern.search(solving_report)
        if dualboundmatch:
            # 提取并返回 Primal bound 值
            dual_bound = dualboundmatch.group(1).strip()
            if dual_bound == 'inf':
                dual_bound = INF  # 替换为 1e20
            elif dual_bound == '-inf':
                dual_bound = -INF  # 替换为 -1e20
            else:
                dual_bound = float(dual_bound)
        else:
            goError = True;
    if not goError:
        match = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+\(objective\)', solving_report)
        if match:
            sol_Obj = float(match.group(1))
    if not goError:
        total_time = re.search(r'Timing\s+(\d+\.\d+)', solving_report)
        if total_time == None:
            goError = True;
        else:
            total_time = float(total_time.group(1))
    # if not goError:
    #     presolve_time = re.search(r'\s*(\d+\.\d+)\s*\(presolve*\)', solving_report)
    #     if presolve_time == None:
    #         goError = True;
    #     else:
    #         presolve_time = float(presolve_time.group(1))
    # if not goError:
    #     postsolve_time = re.search(r'\s*(\d+\.\d+)\s*\(postsolve*\)', solving_report)
    #     if postsolve_time == None:
    #         goError = True;
    #     else:
    #         postsolve_time = float(postsolve_time.group(1))
    if not goError:
        probing_time = re.search(r'\s*(\d+\.\d+)\s*\(probing-first-round*\)', solving_report)
        if probing_time:
            probing_time = float(probing_time_match.group(1))
        else:
            probing_time = 0.0
    if not goError:
        nodes = re.search(r'Nodes\s+(\d+)', solving_report)
        lp_iterations = re.search(r'LP iterations\s+(\d+)', solving_report)
        if nodes == None or lp_iterations == None:
            goError = True;
        else:
            nodes = int(nodes.group(1))
            lp_iterations = int(lp_iterations.group(1))
    
    if goError:
        probname = probname + "." + seed
        info = {
            'file': file_path,
            'name': probname,
            'seed': seed,
            'setting': setting,
            'timelimit': timelimit,
            'status': status,
            'primal_bound': primal_bound,
            'dual_bound': dual_bound,
            'sol_Obj': sol_Obj,
            'gap': gap,
            'total_time': total_time,
            'presolve_time': presolve_time,
            'postsolve_time': postsolve_time,
            'probing_time': probing_time,
            'presolved_row': presolved_row,
            'presolved_col': presolved_col,
            'presolved_nnz': presolved_nnz,
            'binary_vars': binary_vars,
            'integer_vars': integer_vars,
            'implied_int_vars': implied_int_vars,
            'continuous_vars': continuous_vars,
            'nodes': nodes,
            'lp_iterations': lp_iterations,
            'implicationsFirstRound': implicationsFirstRound,
            'fixFirstRound': fixFirstRound,
            'conf': conf,
            'V1': V1,
            'V2': V2,
            'prow': prow,
        }
        ErrorList.append(info)
        print(f"File failed to collect: {file_path}\n")
        return None

    return {
        'file': file_path,
        'name': probname,
        'seed': seed,
        'setting': setting,
        'timelimit': timelimit,
        'status': status,
        'primal_bound': primal_bound,
        'dual_bound': dual_bound,
        'sol_Obj': sol_Obj,
        'gap': gap,
        'total_time': total_time,
        'presolve_time': presolve_time,
        'postsolve_time': postsolve_time,
        'probing_time': probing_time,
        'presolved_row': presolved_row,
        'presolved_col': presolved_col,
        'presolved_nnz': presolved_nnz,
        'binary_vars': binary_vars,
        'integer_vars': integer_vars,
        'implied_int_vars': implied_int_vars,
        'continuous_vars': continuous_vars,
        'nodes': nodes,
        'lp_iterations': lp_iterations,
        'implicationsFirstRound': implicationsFirstRound,
        'fixFirstRound': fixFirstRound,
        'conf': conf,
        'V1': V1,
        'V2': V2,
        'prow': prow,
    }

def find_entry_by_name(name):
    pattern = re.compile(r'^(\S+)\s+(\S+)\s*(\S*)\s*$')

    with open('./benchmark.solu', 'r') as file:
        for line in file:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            match = pattern.match(stripped_line)
            if match:
                identifier, entry_name, value_str = match.groups()
                if entry_name == name:
                    try:
                        value = float(value_str) if value_str else 0.0
                        return {
                            'identifier': identifier,
                            'obj': value
                        }
                    except ValueError:
                        print("obj error!", name)
                        return {
                            'identifier': identifier,
                            'obj': 0.0
                        }

    # 如果没有找到匹配的名字，返回 None
    print("name error!", name)
    return None

def getRealObj(name):
    result = find_entry_by_name(name)
    if not result:
        print(f"No entry found for '{name}'")
        return None
    if result['identifier'] == SOLFILE_OPT:
        return result['obj']
    return None;

def isProblemInfluenced(problemStack, name):
    if problemStack[name][0]['lp_iterations'] != problemStack[name][1]['lp_iterations'] or problemStack[name][0]['nodes'] != problemStack[name][1]['nodes']:
        return True
    else:
        return False

def analyze_instance(info, problemStack):
    if info['status'] == READ_NOT_COLLECT:
        print(f"Status are not collected for '{info['file']}', return now!")
        return
    
    result = find_entry_by_name(info['name'])
    if not result:
        print(f"No entry found for '{info['file']}'")
        return
    if result['identifier'] == SOLFILE_OPT:
        realObj = result['obj'];
        maxObj = max(abs(info['primal_bound']), abs(info['dual_bound']))
        maxObj = max(maxObj, 1.0)
        if info['status'] == READ_OPT:
            if abs(info['sol_Obj'] - realObj) > maxObj * 1e-4:  
                info['status'] = STATUS_MISMATCH
                # print(info)
            elif info['total_time'] >= info['timelimit'] + 100:
                info['status'] = STATUS_TIMEOUT
            else:
                info['status'] = STATUS_SOLVED
        elif info['status'] == READ_INF or info['status'] == READ_UBD:
            info['status'] = STATUS_MISMATCH
            # print(info)
        elif info['status'] == READ_TLIM:
            info['status'] = STATUS_TIMEOUT
        elif info['primal_bound']  < realObj - maxObj * 1e-4 or info['dual_bound'] > realObj + maxObj * 1e-4:
            info['status'] = STATUS_MISMATCH
            # print(info)
        else:
            info['status'] = STATUS_FAIL
    elif result['identifier'] == SOLFILE_UBD:
        info['gap_closed'] = 0
        if info['status'] == READ_UBD:
            info['status'] = STATUS_SOLVED
        elif info['status'] == READ_TLIM:
            info['status'] = STATUS_TIMEOUT
        elif info['dual_bound'] != -INF:
            info['status'] = STATUS_MISMATCH
            # print(info)
        else:
            info['status'] = STATUS_FAIL
    elif result['identifier'] == SOLFILE_INF:
        info['gap_closed'] = 0
        if info['status'] == READ_INF:
            info['status'] = STATUS_SOLVED
        elif info['primal_bound'] <= 0.9 * INF:
            info['status'] = STATUS_MISMATCH
            # print(info)
        elif info['status'] == READ_TLIM:
            info['status'] = STATUS_TIMEOUT
        else:
            info['status'] = STATUS_FAIL
    
    if info['status'] != STATUS_SOLVED:
        info['total_time'] = info['timelimit']

    info['name'] = info['name'] + '.' + info['seed']

    if info['status'] == STATUS_MISMATCH:
        ErrorList.append(info)
    else:
        if info['name'] in problemStack:
            problemStack[info['name']].append(info)
        else:
            problemStack[info['name']] = [info]

def getItem(collect, item, setting, rowSep):
    return collect[item][setting][rowSep]

def getSolvedN(solvedItem, setting, rowSep):
    return solvedItem[setting][rowSep]

def generate_csv_report(settings_dict, output_csv, include_presolved=False, exclude_instances=None):
    """
    生成汇总所有设置的 CSV 报告，每行是一个 (problem, seed) 组合。
    
    settings_dict: {'setting_name': '/path/to/folder', ...}
    output_csv: 输出 CSV 文件路径（自动创建父目录）
    include_presolved: 是否添加 presolved row/col/nnz 列
    exclude_instances: 可选，列表或集合，包含要排除的问题实例名（如 ['dws008-01.5', 'traininstance2.4']）
    """

    if exclude_instances is None:
        exclude_instances = set()
    else:
        exclude_instances = set(exclude_instances)

    # 自动创建输出目录
    out_dir = os.path.dirname(output_csv)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    data = {}
    all_seeds = set()

    for setting, folder in settings_dict.items():
        if not os.path.isdir(folder):
            print(f"Warning: folder {folder} does not exist, skip {setting}")
            continue

        out_files = [f for f in os.listdir(folder) if f.endswith('.out')]
        for out_file in out_files:
            file_path = os.path.join(folder, out_file)
            info = parse_out_file(file_path)
            if info is None:
                print(f"Failed to parse {file_path}, skipping")
                continue

            probname = info['name']   # 实例名（不含种子）

            seed = info['seed']
            try:
                seed_int = int(seed)
            except:
                seed_int = seed

            key = (probname, seed_int)
            all_seeds.add(key)

            if key not in data:
                data[key] = {}
            if setting not in data[key]:
                data[key][setting] = {}

            data[key][setting]['time'] = info.get('total_time', None)
            data[key][setting]['nodes'] = info.get('nodes', None)
            if include_presolved:
                data[key][setting]['rows'] = info.get('presolved_row', None)
                data[key][setting]['cols'] = info.get('presolved_col', None)
                data[key][setting]['nnz'] = info.get('presolved_nnz', None)

    # 排序
    sorted_keys = sorted(list(all_seeds), key=lambda x: (x[0], x[1]))

    # CSV 表头
    fieldnames = ['ProblemName', 'Seed']
    setting_names = list(settings_dict.keys())
    for s in setting_names:
        fieldnames.append(f'T_{s}')
    for s in setting_names:
        fieldnames.append(f'N_{s}')
    if include_presolved:
        for s in setting_names:
            fieldnames.append(f'Rows_{s}')
        for s in setting_names:
            fieldnames.append(f'Cols_{s}')
        for s in setting_names:
            fieldnames.append(f'Nnz_{s}')

    # 写入 CSV
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for probname, seed in sorted_keys:
            if f"{probname}.{seed}" in exclude_instances:
                continue
            row = {'ProblemName': probname, 'Seed': seed}
            # 填充 T
            for s in setting_names:
                rec = data.get((probname, seed), {}).get(s, {})
                row[f'T_{s}'] = rec.get('time', '')
            # 填充 N
            for s in setting_names:
                rec = data.get((probname, seed), {}).get(s, {})
                row[f'N_{s}'] = rec.get('nodes', '')
            # 填充 presolved 分组
            if include_presolved:
                for s in setting_names:
                    rec = data.get((probname, seed), {}).get(s, {})
                    row[f'Rows_{s}'] = rec.get('rows', '')
                for s in setting_names:
                    rec = data.get((probname, seed), {}).get(s, {})
                    row[f'Cols_{s}'] = rec.get('cols', '')
                for s in setting_names:
                    rec = data.get((probname, seed), {}).get(s, {})
                    row[f'Nnz_{s}'] = rec.get('nnz', '')
            writer.writerow(row)


if __name__ == '__main__':
    # base_dir = '/beegfs/home/30150116/lcl/test_new/default' 

    # overallResult = process_folder(base_dir, '/beegfs/home/30150116/lcl/test_new/all')
    # overallResult = process_folder(base_dir, '/beegfs/home/30150116/lcl/test_new/cliquemerge')    
    # overallResult = process_folder(base_dir, '/beegfs/home/30150116/lcl/test_new/linear+obj+two')
    # overallResult = process_folder('/beegfs/home/30150116/lcl/test_new/linear', '/beegfs/home/30150116/lcl/test_new/linear+obj+two')
    # overallResult = process_folder('/beegfs/home/30150116/lcl/test_new/2013', '/beegfs/home/30150116/lcl/test_new/linear+obj+two')         

    base = '/beegfs/home/30150116/lcl/test_new'
    settings = {
        'default': os.path.join(base, 'default'),
        'cliquemerge': os.path.join(base, 'cliquemerge'),
        'linear': os.path.join(base, 'linear'),
        'linear+obj+two': os.path.join(base, 'linear+obj+two'),
        '2013': os.path.join(base, '2013'),
        'all': os.path.join(base, 'all'),
    }
    exclude_list = ['dws008-01.5', 'traininstance2.4']
    generate_csv_report(settings, 'summary.csv', include_presolved=True, exclude_instances=exclude_list)      