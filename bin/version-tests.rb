#!/usr/bin/ruby

$:.unshift File.dirname(__FILE__)

require 'test/unit'
require 'version.rb'

module Version

	class VersionTests < Test::Unit::TestCase

		def test_one
			ver = VersionNumber.new('1')
			assert(ver.to_s() == '1', 'One digit constructor wrong')

			ver.increment()
			assert(ver.to_s() == '2', 'One digit increment wrong')
		end

		def test_two
			ver = VersionNumber.new('1.4')
			assert(ver.to_s() == '1.4', 'Two digit constructor wrong')

			ver.increment()
			assert(ver.to_s() == '1.5', 'One digit increment wrong')
		end

        def test_nonNumeric
			ver = VersionNumber.new('o3d')
            assert(ver != nil)
		end

		def test_three
			ver = VersionNumber.new('5.4.0')
			assert(ver.to_s() == '5.4.0', 'Two digit constructor wrong')

			ver.increment()
			assert(ver.to_s() == '5.4.1', 'One digit increment wrong')
		end
		
		def test_alpha1
			ver = VersionNumber.new('r1')
			assert(ver.to_s() == 'r1', 'One digit alpha constructor wrong')
		end

		def test_alpha2
			ver = VersionNumber.new('3.r2')
			assert(ver.to_s() == '3.r2', 'Two digit alpha constructor wrong')
		end
		
		def test_alpha3
			ver = VersionNumber.new('3.r2.4')
			assert(ver.to_s() == '3.r2.4', 'Three digit alpha constructor wrong')
		end

		def test_compare
			assert(VersionNumber.new('1').compare(VersionNumber.new('1')) == 0)
			assert(VersionNumber.new('1').compare(VersionNumber.new('2')) == -1)
			assert(VersionNumber.new('2').compare(VersionNumber.new('1')) == 1)
			
			assert(VersionNumber.new('1.2').compare(VersionNumber.new('1.2')) == 0)
			assert(VersionNumber.new('1.2').compare(VersionNumber.new('1.3')) == -1)
			assert(VersionNumber.new('1.2').compare(VersionNumber.new('1.1')) == 1)
			assert(VersionNumber.new('1.9').compare(VersionNumber.new('1.10')) == -1)
			assert(VersionNumber.new('1.2').compare(VersionNumber.new('0.95')) == 1)
			
			assert(VersionNumber.new('2').compare(VersionNumber.new('2.1')) == -1)
			assert(VersionNumber.new('2').compare(VersionNumber.new('2.1.2')) == -1)
			assert(VersionNumber.new('2.1').compare(VersionNumber.new('2')) == 1)

			assert(VersionNumber.new('25.0.1352.0').compare(VersionNumber.new('3.0.182.2')) == 1)
		end

		def test_compare_alpha_number
			assert(VersionNumber.new('r1').compare(VersionNumber.new('r2')) == -1)
			assert(VersionNumber.new('1.r1').compare(VersionNumber.new('1.r2')) == -1)
			
			assert(VersionNumber.new('1').compare(VersionNumber.new('r2')) == 1)
			assert(VersionNumber.new('r2').compare(VersionNumber.new('3')) == -1)
			
			assert(VersionNumber.new('1.r1').compare(VersionNumber.new('r2')) == 1)
			assert(VersionNumber.new('r1').compare(VersionNumber.new('1.r2')) == -1)
		
			# Don't support this type yet.
			#assert(VersionNumber.new('3b1').compare(VersionNumber.new('3b2')) == -1)
		end

		def test_compare_alpha_number
			assert_equal(1, VersionNumber.new('782a').compare(VersionNumber.new('782')))
			assert_equal(1, VersionNumber.new('783a').compare(VersionNumber.new('782')))
			assert_equal(-1, VersionNumber.new('782a').compare(VersionNumber.new('783')))
			assert_equal(-1, VersionNumber.new('782').compare(VersionNumber.new('782a')))
			assert_equal(-1, VersionNumber.new('781').compare(VersionNumber.new('782a')))
        end

        def test_operators
			assert(VersionNumber.new('1.2') > VersionNumber.new('1.1'))
			assert(VersionNumber.new('1.2') >= VersionNumber.new('1.1'))
			assert(VersionNumber.new('1.2') >= VersionNumber.new('1.2'))
			assert(!(VersionNumber.new('1.2') < VersionNumber.new('1.1')))
			
            assert(VersionNumber.new('1.2') < VersionNumber.new('1.3'))
            assert(VersionNumber.new('1.2') < VersionNumber.new('1.2.1'))
			assert(VersionNumber.new('1.2') <= VersionNumber.new('1.3'))
			assert(VersionNumber.new('1.2') <= VersionNumber.new('1.2'))

			assert_equal(0, VersionNumber.new('1.2') <=> VersionNumber.new('1.2'))
			assert_equal(1, VersionNumber.new('1.3') <=> VersionNumber.new('1.2'))
			assert_equal(-1,VersionNumber.new('1.2') <=> VersionNumber.new('1.3'))
			
            assert((VersionNumber.new('1.2') == nil) == false)
            assert_equal(1, VersionNumber.new('1.2') <=> nil)
        end
		
        def test_underscores
			ver = VersionNumber.new('1_4')
			assert(ver.to_s() == '1_4', 'Two digit constructor wrong')

			ver.increment()
			assert(ver.to_s() == '1_5', 'Two digit increment wrong')
		end
	end
end
