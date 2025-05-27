set(rlBattleAI_SRCS
		RLBattleAI.cpp
)

set(rlBattleAI_HEADERS
		StdInc.h

		RLBattleAI.h
)

if(NOT ENABLE_STATIC_LIBS)
	list(APPEND rlBattleAI_SRCS main.cpp StdInc.cpp)
endif()
assign_source_group(${rlBattleAI_SRCS} ${rlBattleAI_HEADERS})

if(ENABLE_STATIC_LIBS)
	add_library(RLBattleAI STATIC ${rlBattleAI_SRCS} ${rlBattleAI_HEADERS})
else()
	add_library(RLBattleAI SHARED ${rlBattleAI_SRCS} ${rlBattleAI_HEADERS})
	install(TARGETS RLBattleAI RUNTIME DESTINATION ${AI_LIB_DIR} LIBRARY DESTINATION ${AI_LIB_DIR})
endif()

target_link_libraries(RLBattleAI PRIVATE vcmi)
target_include_directories(RLBattleAI PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

vcmi_set_output_dir(RLBattleAI "AI")
enable_pch(RLBattleAI)
