
# From http://mail.python.org/pipermail/tutor/2004-May/029662.html
# Don Arnold darnold02 at sprynet.com 
# with extra groupings from
# John Miller jmillr at umich.edu

littleNumbers = {'1': 'one', '2': 'two', '3': 'three',
                 '4': 'four', '5': 'five', '6': 'six', '7': 'seven',
                 '8': 'eight', '9': 'nine', '10': 'ten', '11': 'eleven',
                 '12': 'twelve', '13': 'thirteen', '14': 'fourteen',
                 '15': 'fifteen', '16': 'sixteen', '17': 'seventeen',
                 '18': 'eighteen', '19': 'nineteen'
                 }

tens = {'2': 'twenty', '3': 'thirty', '4': 'forty', '5': 'fifty',
        '6': 'sixty', '7': 'seventy', '8': 'eighty', '9': 'ninety'
        }

groupings = ['centillion', 'novemnonagintillion', 'octononagintillion',
              'septnonagintillion', 'sexnonagintillion',  'quinnonagintillion',
              'quattuornonagintillion', 'trenonagintillion',  'duononagintillion',
              'unnonagintillion', 'nonagintillion',  'novemoctogintillion',
              'octooctogintillion', 'septoctogintillion',  'sexoctogintillion',
              'quinoctogintillion', 'quattuoroctogintillion',  'treoctogintillion',
              'duooctogintillion', 'unoctogintillion', 'octogintillion',
              'novemseptuagintillion', 'octoseptuagintillion',  'septseptuagintillion',
              'sexseptuagintillion', 'quinseptuagintillion',  'quattuorseptuagintillion',
              'treseptuagintillion', 'duoseptuagintillion',  'unseptuagintillion',
              'septuagintillion', 'novemsexagintillion',  'octosexagintillion',
              'septsexagintillion', 'sexsexagintillion',  'quinsexagintillion',
              'quattuorsexagintillion', 'tresexagintillion',  'duosexagintillion',
              'unsexagintillion', 'sexagintillion',  'novemquinquagintillion',
              'octoquinquagintillion', 'septquinquagintillion',  'sexquinquagintillion',
              'quinquinquagintillion', 'quattuorquinquagintillion',  'trequinquagintillion',
              'duoquinquagintillion', 'unquinquagintillion',  'quinquagintillion',
              'novemquadragintillion', 'octoquadragintillion',  'septquadragintillion',
              'sexquadragintillion', 'quinquadragintillion',  'quattuorquadragintillion',
              'trequadragintillion', 'duoquadragintillion',  'unquadragintillion',
              'quadragintillion', 'novemtrigintillion',  'octotrigintillion',
              'septtrigintillion', 'sextrigintillion',  'quintrigintillion',
              'quattuortrigintillion', 'tretrigintillion',  'duotrigintillion',
              'untrigintillion', 'trigintillion', 'novemvigintillion',  'octovigintillion',
              'septvigintillion', 'sexvigintillion', 'quinvigintillion',
              'quattuorvigintillion', 'trevigintillion',  'duovigintillion',
              'unvigintillion', 'vigintillion', 'novemdecillion',  'octodecillion',
              'septdecillion', 'sexdecillion', 'quindecillion',  'quattuordecillion',
              'tredecillion', 'duodecillion', 'undecillion',  'decillion', 'nonillion',
              'octillion', 'septillion', 'sextillion', 'quintillion',
              'quadrillion', 'trillion', 'billion', 'million',  'thousand', ''
              ]

def getCheckNumber(num):
    maxDigits = 306
    result = []
    group = 0

    if num < 0:
        result.append('negative')
        num = abs(num)

    num = str(num).zfill(maxDigits)

    if len(num) > maxDigits:
        raise 'Number too large'
   
    for i in range(0, maxDigits - 1, 3):
        chunk = num[i:i+3]
        if chunk != '000':
            if chunk[0] != '0':
                result.append(littleNumbers[chunk[0]])
                result.append('hundred')

            if chunk[1] == '1':
                result.append(littleNumbers[chunk[1:3]])
            else:
                tensString = ''
                if chunk[1] != '0':
                    if chunk[2] != '0':
                        tensString += tens[chunk[1]] + '-'
                    else:
                        tensString += tens[chunk[1]]

                if chunk[2] != '0':
                    tensString += littleNumbers[chunk[2]]

                if tensString:
                    result.append(tensString)
                    
            if groupings[group]:
                result.append(groupings[group] + ',')
        group += 1

    if not result:
        return 'zero'
    else:
        result = ' '.join(result)
        
        if result.endswith(','):
            result = result[:-1]
            
        return result

def main():
    while 1:
        print
        num = int(raw_input('Enter an integer (0 to quit): '))
        print getCheckNumber(num)
        if num == 0:
            break
    
if __name__ == '__main__':
    main()
    