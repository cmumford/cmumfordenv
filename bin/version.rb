#!/usr/bin/ruby

#
# A simple class to handle version numbers in "dot" notation
# like "1", "1.0", "1.1.0", etc.
#

module Version
	class VersionNumber
		attr_accessor :values, :delimiter
		def initialize(version, delim='.')
            self.delimiter = delim
            if isUnderscoreDelimited(version) then
                self.delimiter = '_'
            end
			self.values = version.split(self.delimiter)
		end

		def to_s()
			return self.values.join(delimiter)
		end

		def increment()
			idx = values.length-1
			values[idx] = (Integer(values[idx]) + 1).to_s()
		end

		def append(value)
			values.push(value)
		end

		@staticmethod
		def sign(intA, intB)
			if intA < intB then
				return -1
			elsif intA > intB then
				return 1
			else
				return 0
			end 
		end

        @staticmethod
        def isUnderscoreDelimited(value)
			if value != nil and value.index('_') != -1 and value =~ /^[\d_]+$/ then
                return true
            else
                return false
            end
        end

        @staticmethod
        def isNumberAlpha(value)
			if value != nil and value =~ /^(\d+)(\D*)$/ then
                return true
            else
                return false
            end
        end

        @staticmethod
        def isAlphaNumber(value)
            if value != nil and value =~ /^(\D+)(\d*)$/ then
                return true
            else
                return false
            end
        end

        @staticmethod
		def compareValuesNumberAlpha(lhs, rhs)
			lText = nil
			lNum  = nil
			rText = nil
			rNum  = nil

			if lhs =~ /^(\d+)(\D*)$/ then
				lNum  = Integer($1)
				lText = $2 if $2 != ''
			else
                begin
				    lNum = Integer(lhs)
                rescue
                    lText = lhs
                end
			end

			if rhs =~ /^(\d+)(\D*)$/ then
				rNum  = Integer($1)
				rText = $2 if $2 != ''
			else
                begin
				    rNum = Integer(rhs)
                rescue
                    rText = rhs
                end
			end

            if lNum != nil && rNum != nil then
                s = lNum <=> rNum
                if s != 0 then
                    return s
                end
            end

            if (lText != nil || rText != nil) && lNum != nil && lNum == rNum then
                if lText != nil and rText == nil then
                    return 1
                elsif lText == nil and rText != nil then
                    return -1
                else
                    return lText <=> rText
                end
            end

			if lText == nil and rText != nil then
				return 1
			elsif lText != nil and rText == nil then
				return -1
			elsif lText != nil and rText != nil then
				sign = lText <=> rText
				return sign if sign != 0
			end

			return sign(lNum, rNum)
		end

		@staticmethod
		def compareValuesAlphaNumber(lhs, rhs)
			lText = nil
			lNum  = nil
			rText = nil
			rNum  = nil

			if lhs =~ /^(\D+)(\d*)$/ then
				lText = $1
				lNum  = Integer($2) if $2 != ""
			else
                begin
				    lNum = Integer(lhs)
                rescue
                    lText = lhs
                end
			end
			
			if rhs =~ /^(\D+)(\d*)$/ then
				rText = $1
				rNum  = Integer($2) if $2 != ""
			else
                begin
				    rNum = Integer(rhs)
                rescue
                    rText = rhs
                end
			end

            if (lText != nil || rText != nil) && lNum != nil && lNum == rNum then
                if lText != nil and rText == nil then
                    return 1
                elsif lText == nil and rText != nil then
                    return -1
                else
                    return lText <=> rText
                end
            end

			if lText == nil and rText != nil then
				return 1
			elsif lText != nil and rText == nil then
				return -1
			elsif lText != nil and rText != nil then
				sign = lText <=> rText
				return sign if sign != 0
			end

			return sign(lNum, rNum)
		end

        @staticmethod
		def compareValues(lhs, rhs)
            if isAlphaNumber(lhs) then
                return compareValuesAlphaNumber(lhs, rhs)
            elsif isNumberAlpha(lhs) then
                return compareValuesNumberAlpha(lhs, rhs)
            elsif isAlphaNumber(rhs) then
                return compareValuesAlphaNumber(lhs, rhs)
            else
                return compareValuesNumberAlpha(lhs, rhs)
            end
		end

		def compare(rhs)
			selflen = self.values.length
			rhslen = rhs.values.length
			max = selflen > rhslen ? selflen : rhslen
			for i in (0..max)
				sign = compareValues(self.values[i], rhs.values[i])
				return sign if sign != 0
			end

			if selflen > rhslen then
				return 1
			elsif rhslen > selflen then
				return -1
			else
				return 0
			end
		end

        def < (rhs)
            return compare(rhs) < 0
        end
        
        def <= (rhs)
            return compare(rhs) <= 0
        end
        
        def > (rhs)
            return compare(rhs) > 0
        end
        
        def >= (rhs)
            return compare(rhs) >= 0
        end
        
        def == (rhs)
            if rhs.class == VersionNumber
                return compare(rhs) == 0
            else
                return false
            end
        end
        
        def <=> (rhs)
            if rhs.class == VersionNumber
                return compare(rhs)
            else
                return 1
            end
        end
	end
end
